"""HTTP status codes.

The original project imported these constants from its web framework, and the
tests referred to them as ``status.HTTP_201_CREATED``.  The names and values
are the standard ones, so the test bodies keep reading exactly as before.
"""

HTTP_200_OK = 200
HTTP_201_CREATED = 201
HTTP_202_ACCEPTED = 202
HTTP_204_NO_CONTENT = 204
HTTP_400_BAD_REQUEST = 400
HTTP_401_UNAUTHORIZED = 401
HTTP_403_FORBIDDEN = 403
HTTP_404_NOT_FOUND = 404
HTTP_405_METHOD_NOT_ALLOWED = 405
HTTP_406_NOT_ACCEPTABLE = 406
HTTP_415_UNSUPPORTED_MEDIA_TYPE = 415
HTTP_500_INTERNAL_SERVER_ERROR = 500
