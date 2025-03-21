from rest_framework import status
from rest_framework.response import Response


class CustomResponseMixin:
    """
    A mixin to provide custom responses for list, retrieve, create, update, and destroy methods.
    Handles errors and empty data by setting success = False.
    """

    def _custom_response(self, data, message, success=True, status_code=status.HTTP_200_OK):
        """
        Helper method to create a custom response.
        """
        return Response({
            'success': success,
            'message': message,
            'data': data
        }, status=status_code)

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        if not response.data:
            return self._custom_response([], 'No data found', success=False, status_code=status.HTTP_200_OK)
        return self._custom_response(response.data, 'Data retrieved successfully')

    def retrieve(self, request, *args, **kwargs):
        try:
            response = super().retrieve(request, *args, **kwargs)
            return self._custom_response(response.data, 'Data retrieved successfully')
        except Exception as e:
            return self._custom_response({}, str(e), success=False, status_code=status.HTTP_404_NOT_FOUND)

    def create(self, request, *args, **kwargs):
        try:
            response = super().create(request, *args, **kwargs)
            return self._custom_response(response.data, 'Data created successfully', status_code=status.HTTP_201_CREATED)
        except Exception as e:
            return self._custom_response({}, str(e), success=False, status_code=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        try:
            response = super().update(request, *args, **kwargs)
            return self._custom_response(response.data, 'Data updated successfully')
        except Exception as e:
            return self._custom_response({}, str(e), success=False, status_code=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, *args, **kwargs):
        try:
            response = super().partial_update(request, *args, **kwargs)
            return self._custom_response(response.data, 'Data partially updated successfully')
        except Exception as e:
            return self._custom_response({}, str(e), success=False, status_code=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        try:
            super().destroy(request, *args, **kwargs)
            return self._custom_response({}, 'Data deleted successfully', status_code=status.HTTP_200_OK)
        except Exception as e:
            return self._custom_response({}, str(e), success=False, status_code=status.HTTP_400_BAD_REQUEST)
