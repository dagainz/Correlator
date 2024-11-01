
from concurrent import futures
import asyncio
import argparse
import logging
import os
from typing import Optional, Callable, Awaitable, Any
import pickle

from rstream import AMQPMessage, Producer

import frontend_record_pb2_grpc
import frontend_record_pb2
import grpc

from grpc_interceptor import AsyncServerInterceptor
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
    },
    {
        'rabbitmq_host': {
            'default': 'docker1',
            'desc': 'The RabbitMQ server host name.',
            'type': ConfigType.STRING
        }
    },
    {
        'rabbitmq_user': {
            'default': 'guest',
            'desc': 'The RabbitMQ username',
            'type': ConfigType.STRING
        }
    },
    {
        'rabbitmq_password': {
            'default': 'guest',
            'desc': '*TRANSITIONAL* The RabbitMQ password',
            'type': ConfigType.STRING
        }
    },
    {
        'rabbitmq_input_stream': {
            'default': 'Correlator-input',
            'desc': 'The name of the RabbitMQ input stream',
            'type': ConfigType.STRING
        }
    },
    {
        'rabbitmq_event_stream': {
            'default': 'Correlator-event',
            'desc': 'The name of the RabbitMQ event stream',
            'type': ConfigType.STRING
        }
    }

]


class FrontEndInputServicer(frontend_record_pb2_grpc.FrontEndInputServicer):

    record_types = {x.value: x.name for x in RecordTypes}

    def __init__(self, producer: Producer, stream: str) -> None:
        # log.info('In constructor')
        self.producer = producer
        self.stream = stream
        self.lock = asyncio.Lock()

    async def _send(self, record):
        """Sends syslog record to rabbitmq"""
        await self.lock.acquire()
        payload = AMQPMessage(
                body=pickle.dumps(record)
            )
        try:
            await self.producer.send(stream=self.stream, message=payload)
        finally:
            self.lock.release()

    async def ProcessRecord(self, iterator, context):
        async for record in iterator:
            if record.type == RecordTypes.HEARTBEAT.value:
                log.info('Ignoring heartbeat')
            elif record.type == RecordTypes.SYSLOG_DATA:
                log.info('Sending syslog record to rabbitmq stream')
                await self.lock.acquire()
                payload = AMQPMessage(
                    body=pickle.dumps(record)
                )
                try:
                    await self.producer.send(stream=self.stream, message=payload)
                finally:
                    self.lock.release()
            else:
                log.error(f'Unknown record type: {record.type} for {record.tenant_id} from {record.source_id}')

        return frontend_record_pb2.Result(code=0, message='OK')

    # async def _send(self, record):
    #     log.info(f'sending {self.record_types[record.type]} record')


class LoggingInterceptor(AsyncServerInterceptor):

    method_map = {
        '/FrontEndInput/ProcessRecord': 'A request to open an input data stream'
    }

    # async def intercept_service(self, continuation: Callable[
    #     [grpc.HandlerCallDetails], Awaitable[grpc.RpcMethodHandler]
    # ], handler_call_details: grpc.HandlerCallDetails) -> grpc.RpcMethodHandler:
    #     log.info(f'{handler_call_details}')
    #
    #     return await continuation(handler_call_details)
    async def intercept(
            self,
            method: Callable,
            request: Any,
            context: grpc.ServicerContext,
            method_name: str,
    ) -> Any:
        desc = self.method_map.get(method_name, f'An unexpected request called {method_name}')
        log.info(f'{desc} from {context.peer()} accepted')
        return await method(request, context)


class InputProcessorCLI:
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

        self.grpc_listen_addr = f'{grpc_host}:{grpc_port}'

        asyncio.run(self._server(), debug=args.debug)

    async def _server(self) -> None:

        # RabbitMQ
        rmq_host = RuntimeConfig.get('input_processor.rabbitmq_host')
        rmq_user = RuntimeConfig.get('input_processor.rabbitmq_user')

        # Need to replace with hook into keyring here

        log.info(f'connnecting to rabbitmq {rmq_host}:{rmq_user}')
        rmq_password = RuntimeConfig.get('input_processor.rabbitmq_password')

        async with Producer(rmq_host, username=rmq_user, password=rmq_password) as producer:
            log.info(f'Connected to RabbitMQ server at {rmq_host}')
            # await producer.create_stream('Correlator', exists_ok=True)

        # gRPC

            stream = RuntimeConfig.get('input_processor.rabbitmq_input_stream')
            interceptors = [LoggingInterceptor()]
            server = grpc.aio.server(interceptors=interceptors)
            frontend_record_pb2_grpc.add_FrontEndInputServicer_to_server(FrontEndInputServicer(producer, stream), server)
            server.add_insecure_port(self.grpc_listen_addr)
            await server.start()
            log.info(f"Async server started, listening for gRPC requests on {self.grpc_listen_addr}")
            await server.wait_for_termination()
            log.info('Await complete')

   # async def _server(self) -> None:
   #      # RabbitMQ
   #
   #      log.info('Connecting to RabbitMQ')
   #      async with Producer("docker1", username="guest", password="guest") as producer:
   #          log.info('Creating stream if it does not exist')
   #          await producer.create_stream('Correlator', exists_ok=True)
   #
   #      # gRPC
   #
   #          # interceptors = [LoggingInterceptor()]
   #          interceptors = None
   #          server = grpc.aio.server(interceptors=interceptors)
   #          frontend_record_pb2_grpc.add_FrontEndInputServicer_to_server(FrontEndInput(producer), server)
   #          server.add_insecure_port(self.listen_addr)
   #          await server.start()
   #          log.info(f"Async server started, listening for gRPC requests on {self.listen_addr}")
   #          await server.wait_for_termination()


if __name__ == "__main__":
    InputProcessorCLI()
