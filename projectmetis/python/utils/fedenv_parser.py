import yaml

import projectmetis.python.utils.proto_messages_factory as proto_messages_factory


class Docker(object):

    def __init__(self, docker_image):
        self.docker_image = docker_image


class TerminationSignals(object):

    def __init__(self, termination_signals_map):
        self.federation_rounds = termination_signals_map.get("FederationRounds", 100)
        self.execution_time_cutoff_mins = termination_signals_map.get("ExecutionCutoffTimeMins", 1e6)
        self.metric_cutoff_score = termination_signals_map.get("MetricCutoffScore", 1)


class CommunicationProtocol(object):

    def __init__(self, communication_protocol):
        self.name = communication_protocol
        self.is_synchronous = communication_protocol == "SYNCHRONOUS"
        self.is_asynchronous = communication_protocol == "ASYNCHRONOUS"


class GlobalModelConfig(object):

    def __init__(self, global_model_map):
        self.aggregation_function = global_model_map.get("AggregationFunction", "FedAvg")
        self.participation_ratio = global_model_map.get("ParticipationRatio", 1)


class LocalModelConfig(object):

    def __init__(self, local_model_map):
        self.batch_size = local_model_map.get("BatchSize", 100)
        self.local_epochs = local_model_map.get("LocalEpochs", 5)
        self.validation_percentage = local_model_map.get("ValidationPercentage", 0)
        self.optimizer_config = OptimizerConfig(local_model_map.get("OptimizerConfig"))


class OptimizerConfig(object):

    def __init__(self, optimizer_map):
        self.optimizer_name = optimizer_map.get("OptimizerName")
        self.learning_rate = optimizer_map.get("LearningRate")
        self.optimizer_pb = self.create_optimizer_pb(optimizer_map)

    def create_optimizer_pb(self, optimizer_map):
        optimizer_kwargs = dict()
        optimizer_kwargs["learning_rate"] = self.learning_rate
        if self.optimizer_name == "VanillaSGD":
            if "L1Reg" in optimizer_map:
                optimizer_kwargs["l1_reg"] = optimizer_map['L1Reg']
            if "L2Reg" in optimizer_map:
                optimizer_kwargs["l2_reg"] = optimizer_map['L2Reg']
            optimizer_pb = proto_messages_factory.ModelProtoMessages \
                .construct_vanilla_sgd_optimizer_pb(**optimizer_kwargs)
        elif self.optimizer_name == "MomentumSGD":
            if "MomentumFactor" in optimizer_map:
                optimizer_kwargs["momentum_factor"] = optimizer_map['MomentumFactor']
            optimizer_pb = proto_messages_factory.ModelProtoMessages \
                .construct_momentum_sgd_optimizer_pb(**optimizer_kwargs)
        elif self.optimizer_name == "FedProx":
            if "ProximalTerm" in optimizer_map:
                optimizer_kwargs["proximal_term"] = optimizer_map['ProximalTerm']
            optimizer_pb = proto_messages_factory.ModelProtoMessages \
                .construct_fed_prox_optimizer_pb(**optimizer_kwargs)
        elif self.optimizer_name == "Adam":
            if "Beta1" in optimizer_map:
                optimizer_kwargs["beta_1"] = optimizer_map['Beta1']
            if "Beta2" in optimizer_map:
                optimizer_kwargs["beta_2"] = optimizer_map['Beta2']
            if "Epsilon" in optimizer_map:
                optimizer_kwargs["epsilon"] = optimizer_map['Epsilon']
            optimizer_pb = proto_messages_factory.ModelProtoMessages \
                .construct_adam_optimizer_pb(**optimizer_kwargs)
        optimizer_pb = proto_messages_factory.ModelProtoMessages \
            .construct_optimizer_config_pb(optimizer_pb=optimizer_pb)
        return optimizer_pb


class Controller(object):

    def __init__(self, controller_map):
        self.project_home = controller_map.get("ProjectHome", None)
        self.connection_configs = ConnectionConfigs(controller_map.get("ConnectionConfigs"))
        self.grpc_servicer = GRPCServicer(controller_map.get("GRPCServicer"))


class Learners(object):

    def __init__(self, learners_map):
        self.learners = []
        for learner_def in learners_map:
            self.learners.append(Learner(learner_def))

    def __iter__(self):
        self.itr_index = 0
        return self

    def __next__(self):
        end = len(self.learners)
        if self.itr_index >= end:
            raise StopIteration
        current = self.learners[self.itr_index]
        self.itr_index += 1
        return current


class Learner(object):

    def __init__(self, learner_def_map):
        self.learner_id = learner_def_map.get("LearnerID")
        self.project_home = learner_def_map.get("ProjectHome", None)
        self.connection_configs = ConnectionConfigs(learner_def_map.get("ConnectionConfigs"))
        self.grpc_servicer = GRPCServicer(learner_def_map.get('GRPCServicer'))
        self.cuda_devices = learner_def_map.get('CudaDevices', [])
        self.dataset_configs = DatasetConfigs(learner_def_map.get("DatasetConfigs"))


class ConnectionConfigs(object):

    def __init__(self, connection_configs_map):
        self.hostname = connection_configs_map.get("Hostname", "localhost")
        self.username = connection_configs_map.get("Username", "")
        self.password = connection_configs_map.get("Password", "")
        self.key_filename = connection_configs_map.get("KeyFilename", "")
        self.passphrase = connection_configs_map.get("Passphrase", "")
        self.on_login = connection_configs_map.get("OnLogin", "clear")

    def get_netmiko_connection_config(self):
        conn_config = {
            "device_type": "linux",
            "host": self.hostname,
            "username": self.username,
            "password": self.password
        }
        return conn_config

    def get_fabric_connection_config(self):
        connect_kwargs = {
            "password": self.password,
            "key_filename": self.key_filename,
            "passphrase": self.passphrase
        }
        conn_config = {
            "host": self.hostname,
            "user": self.username,
            "connect_kwargs": connect_kwargs
        }
        return conn_config


class DatasetConfigs(object):

    def __init__(self, dataset_configs_map):
        self.train_dataset_path = dataset_configs_map.get("TrainDatasetPath")
        self.validation_dataset_path = dataset_configs_map.get("ValidationDatasetPath", "")
        self.test_dataset_path = dataset_configs_map.get("TestDatasetPath", "")


class GRPCServicer(object):

    def __init__(self, grpc_servicer_map):
        self.port = grpc_servicer_map.get("Port")


class FederationEnvironment(object):

    def __init__(self, federation_environment_config_fp):
        # Read YAML Configs.
        fstream = open(federation_environment_config_fp).read()
        loaded_stream = yaml.load(fstream, Loader=yaml.SafeLoader)

        federation_environment = loaded_stream.get("FederationEnvironment")
        self.docker = Docker(federation_environment.get("DockerImage"))
        self.termination_signals = TerminationSignals(federation_environment.get("TerminationSignals"))
        self.evaluation_metric = federation_environment.get("EvaluationMetric")
        self.communication_protocol = CommunicationProtocol(federation_environment.get("CommunicationProtocol"))
        self.global_model_config = GlobalModelConfig(federation_environment.get("GlobalModelConfig"))
        self.local_model_config = LocalModelConfig(federation_environment.get("LocalModelConfig"))
        self.controller = Controller(federation_environment.get("Controller"))
        self.learners = Learners(federation_environment.get("Learners"))
