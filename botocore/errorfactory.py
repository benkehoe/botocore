# Copyright 2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
from botocore.exceptions import ClientError
from botocore.utils import get_service_module_name


class BaseClientExceptions(object):
    ClientError = ClientError

    def __init__(self, code_to_exception=None):
        """Base class for exceptions object on a client

        :type code_to_exception: dict
        :param code_to_exception: Mapping of error codes (strings) to exception
            class that should be raised when encountering a particular
            error code.
        """
        self._code_to_exception = code_to_exception
        if code_to_exception is None:
            self._code_to_exception = {}

    def from_code(self, error_code):
        """Retrieves the error class based on the error code

        This is helpful for identifying the exception class needing to be
        caught based on the ClientError.parsed_reponse['Error']['Code'] value

        :type error_code: string
        :param error_code: The error code associated to a ClientError exception

        :rtype: ClientError or a subclass of ClientError
        :returns: The appropriate modeled exception class for that error
            code. If the error code does not match any of the known
            modeled exceptions then return a generic ClientError.
        """
        return self._code_to_exception.get(error_code, self.ClientError)


class ClientExceptionsFactory(object):
    def __init__(self):
        self._client_exceptions_cache = {}

    def create_client_exceptions(self, service_model):
        """Creates a ClientExceptions object for the particular service client

        :type service_model: botocore.model.ServiceModel
        :param service_model: The service model for the client

        :rtype: object that subclasses from BaseClientExceptions
        :returns: The exceptions object of a client that can be used
            to grab the various different modeled exceptions.
        """
        service_name = service_model.service_name
        if service_name not in self._client_exceptions_cache:
            client_exceptions = self._create_client_exceptions(service_model)
            self._client_exceptions_cache[service_name] = client_exceptions
        return self._client_exceptions_cache[service_name]

    def _create_client_exceptions(self, service_model):
        cls_props = {}
        code_to_exception = {}
        for op_name in service_model.operation_names:
            op_model = service_model.operation_model(op_name)
            for shape in op_model.error_shapes:
                exception_name = str(shape.name)
                # An exception can be in multiple operations.
                # So as an optimization, only create a new class and
                # add it to the class properties if has not been included
                # already.
                if exception_name not in cls_props:
                    exception_cls = type(exception_name, (ClientError,), {})
                    code = shape.metadata.get("error", {}).get("code")
                    cls_props[exception_name] = exception_cls
                    if code:
                        code_to_exception[code] = exception_cls
                    else:
                        # Use the exception name if there is no explicit code
                        # modeled
                        code_to_exception[exception_name] = exception_cls
        cls_name = str(get_service_module_name(service_model) + 'Exceptions')
        client_exceptions_cls = type(
            cls_name, (BaseClientExceptions,), cls_props)
        return client_exceptions_cls(code_to_exception)
