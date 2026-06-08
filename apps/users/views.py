from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import (
    extend_schema,
    OpenApiExample,
)

from .serializers import (
    SignupSerializer,
    SignupResponseSerializer,
)


class SignupView(APIView):

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Authentication"],
        summary="Register a new user",
        description="""
        Create a new account.

        Allowed roles:
        - CUSTOMER
        - AUTHOR

        ADMIN registration is not allowed.
        """,
        request=SignupSerializer,
        responses={
            201: SignupResponseSerializer,
        },
        examples=[
            OpenApiExample(
                "Customer Signup",
                value={
                    "email": "customer@gmail.com",
                    "password": "Customer@123",
                    "first_name": "John",
                    "last_name": "Doe",
                    "phone": "+919876543210",
                    "role": "CUSTOMER",
                },
                request_only=True,
            ),
            OpenApiExample(
                "Author Signup",
                value={
                    "email": "author@gmail.com",
                    "password": "Author@123",
                    "first_name": "Jane",
                    "last_name": "Smith",
                    "phone": "+919876543210",
                    "role": "AUTHOR",
                },
                request_only=True,
            ),
        ],
    )
    def post(self, request):

        serializer = SignupSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        user = serializer.save()

        return Response(
            {
                "message": "Registration successful",
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "role": user.role,
                    "full_name": user.full_name,
                }
            },
            status=status.HTTP_201_CREATED
        )