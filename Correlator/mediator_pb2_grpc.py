# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
"""Client and server classes corresponding to protobuf-defined services."""
import grpc
import warnings

import mediator_pb2 as mediator__pb2

GRPC_GENERATED_VERSION = '1.66.2'
GRPC_VERSION = grpc.__version__
_version_not_supported = False

try:
    from grpc._utilities import first_version_is_lower
    _version_not_supported = first_version_is_lower(GRPC_VERSION, GRPC_GENERATED_VERSION)
except ImportError:
    _version_not_supported = True

if _version_not_supported:
    raise RuntimeError(
        f'The grpc package installed is at version {GRPC_VERSION},'
        + f' but the generated code in mediator_pb2_grpc.py depends on'
        + f' grpcio>={GRPC_GENERATED_VERSION}.'
        + f' Please upgrade your grpc module to grpcio>={GRPC_GENERATED_VERSION}'
        + f' or downgrade your generated code using grpcio-tools<={GRPC_VERSION}.'
    )


class MediatorStub(object):
    """Interface exported by the mediator server.

    For the TCP Syslog Source (in the Sources/TCP_Syslog directory):

    python -m grpc_tools.protoc -I../../proto --python_out=. --grpc_python_out=. ../../proto/mediator.proto

    For the input processor: (in the main source directory):

    python -m grpc_tools.protoc -Iproto --python_out=. --grpc_python_out=. proto/mediator.proto

    """

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.StreamSourceData = channel.stream_unary(
                '/Mediator/StreamSourceData',
                request_serializer=mediator__pb2.SourceRecord.SerializeToString,
                response_deserializer=mediator__pb2.Result.FromString,
                _registered_method=True)
        self.DispatchEvent = channel.unary_unary(
                '/Mediator/DispatchEvent',
                request_serializer=mediator__pb2.EventRecord.SerializeToString,
                response_deserializer=mediator__pb2.Result.FromString,
                _registered_method=True)
        self.ConnectionTest = channel.unary_unary(
                '/Mediator/ConnectionTest',
                request_serializer=mediator__pb2.Empty.SerializeToString,
                response_deserializer=mediator__pb2.Result.FromString,
                _registered_method=True)


class MediatorServicer(object):
    """Interface exported by the mediator server.

    For the TCP Syslog Source (in the Sources/TCP_Syslog directory):

    python -m grpc_tools.protoc -I../../proto --python_out=. --grpc_python_out=. ../../proto/mediator.proto

    For the input processor: (in the main source directory):

    python -m grpc_tools.protoc -Iproto --python_out=. --grpc_python_out=. proto/mediator.proto

    """

    def StreamSourceData(self, request_iterator, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def DispatchEvent(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def ConnectionTest(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')


def add_MediatorServicer_to_server(servicer, server):
    rpc_method_handlers = {
            'StreamSourceData': grpc.stream_unary_rpc_method_handler(
                    servicer.StreamSourceData,
                    request_deserializer=mediator__pb2.SourceRecord.FromString,
                    response_serializer=mediator__pb2.Result.SerializeToString,
            ),
            'DispatchEvent': grpc.unary_unary_rpc_method_handler(
                    servicer.DispatchEvent,
                    request_deserializer=mediator__pb2.EventRecord.FromString,
                    response_serializer=mediator__pb2.Result.SerializeToString,
            ),
            'ConnectionTest': grpc.unary_unary_rpc_method_handler(
                    servicer.ConnectionTest,
                    request_deserializer=mediator__pb2.Empty.FromString,
                    response_serializer=mediator__pb2.Result.SerializeToString,
            ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
            'Mediator', rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))
    server.add_registered_method_handlers('Mediator', rpc_method_handlers)


 # This class is part of an EXPERIMENTAL API.
class Mediator(object):
    """Interface exported by the mediator server.

    For the TCP Syslog Source (in the Sources/TCP_Syslog directory):

    python -m grpc_tools.protoc -I../../proto --python_out=. --grpc_python_out=. ../../proto/mediator.proto

    For the input processor: (in the main source directory):

    python -m grpc_tools.protoc -Iproto --python_out=. --grpc_python_out=. proto/mediator.proto

    """

    @staticmethod
    def StreamSourceData(request_iterator,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.stream_unary(
            request_iterator,
            target,
            '/Mediator/StreamSourceData',
            mediator__pb2.SourceRecord.SerializeToString,
            mediator__pb2.Result.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def DispatchEvent(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/Mediator/DispatchEvent',
            mediator__pb2.EventRecord.SerializeToString,
            mediator__pb2.Result.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def ConnectionTest(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/Mediator/ConnectionTest',
            mediator__pb2.Empty.SerializeToString,
            mediator__pb2.Result.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)
