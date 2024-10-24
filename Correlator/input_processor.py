
from concurrent import futures
import argparse
import logging
import os
from typing import Optional, Callable, Awaitable, Any

import frontend_record_pb2_grpc
import frontend_record_pb2
import grpc
from grpc_interceptor import ServerInterceptor

from Correlator.config_store import RuntimeConfig, ConfigType
from Correlator.app_config import ApplicationConfig

from Correlator.core import setup_root_logger, RecordTypes, ResultCodes, Instance

log = logging.getLogger(__name__)

InputConfig = [
    {
        'grpc_listen_address': {
            'default': '0.0.0.0',
            'desc': 'The IPv4 address of the interface to listen for gRPC requests.',
            'type': ConfigType.STRING
        }
    },
    {
        'grpc_listen_port': {
            'default': 50051,
            'desc': 'The port number to listen on for gRPC requests.',
            'type': ConfigType.INTEGER
        }
    }

]


class FrontEndInputServicer(frontend_record_pb2_grpc.FrontEndInputServicer):
    def ProcessRecord(self, iterator, context):
        for record in iterator:
            # if record.type not in RecordTypes:
            #     log.error(f'Unknown record type: {record.type} for {record.tenant_id} from {record.source_id}')
            # else:
            typename = RecordTypes(record.type).name
            log.info(f'Got {typename} for tenant {record.tenant_id} from source id {record.source_id}')
        return frontend_record_pb2.Result(code=ResultCodes.OK, message='OK')


class LoggingInterceptor(ServerInterceptor):

    method_map = {
        '/FrontEndInput/ProcessRecord': 'A request to open an input data stream'
    }

    def intercept(
            self,
            method: Callable,
            request: Any,
            context: grpc.ServicerContext,
            method_name: str,
    ) -> Any:
        desc = self.method_map.get(method_name, f'An unexpected request called {method_name}')
        log.info(f'{desc} from {context.peer()} accepted')
        return method(request, context)


class CLI:
    def __init__(self):
        self.log = log.getChild('input_processor')
        parser = argparse.ArgumentParser(description='Correlator input processor')
        parser.add_argument(
            '--config_file',
            required=True,
            help='Configuration file to use'
        )
        parser.add_argument('-d', '--debug', action='store_true', help='Enable verbose output')

        args = parser.parse_args()

        # For Runtime configuration
        RuntimeConfig.add(InputConfig, 'input_processor')

        if 'CORRELATOR_CFG' in os.environ:
            final_config_file = os.environ['CORRELATOR_CFG']
            self.log.debug(f'CORRELATOR_CFG environment variable set. Using its'
                           f' value of  {final_config_file}')
        else:
            final_config_file = args.config_file
            self.log.debug(f'CORRELATOR_CFG environment variable not set.'
                           f' Using the preset value of {final_config_file}')

        if not ApplicationConfig.load(final_config_file):
            raise ValueError('Cannot load configuration file')

        if args.debug:
            level = logging.DEBUG
        else:
            level = logging.INFO

        setup_root_logger(level)

        log.info(f'Correlator {Instance.Version} Input processor startup')
        RuntimeConfig.dump_to_log()

        grpc_host = RuntimeConfig.get('input_processor.grpc_listen_address')
        grpc_port = RuntimeConfig.get('input_processor.grpc_listen_port')

        grpc_hostport = f'{grpc_host}:{grpc_port}'

        interceptors = [LoggingInterceptor()]
        server = grpc.server(
            futures.ThreadPoolExecutor(max_workers=10),
            interceptors=interceptors)
        frontend_record_pb2_grpc.add_FrontEndInputServicer_to_server(FrontEndInputServicer(), server)

        server.add_insecure_port(grpc_hostport)
        server.start()
        log.info(f"Server started, listening for gRPC requests on {grpc_hostport}")
        server.wait_for_termination()


if __name__ == "__main__":
    CLI()
