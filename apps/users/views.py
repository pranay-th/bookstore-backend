from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import (
    SignupSerializer,
    SignupResponseSerializer,
    LoginSerializer,
    LoginResponseSerializer,
)
from drf_spectacular.utils import (
    extend_schema,
    OpenApiExample,
    OpenApiResponse,
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


class LoginView(APIView):

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Authentication"],
        summary="Login user",
        description="""
        Authenticate with email and password.

        Returns user details on success.
        User role is detected automatically — no need to specify it.

        **Roles supported:** CUSTOMER, AUTHOR, ADMIN
        """,
        request=LoginSerializer,
        responses={
            200: OpenApiResponse(
                response=LoginResponseSerializer,
                description="Login successful",
                examples=[
                    OpenApiExample(
                        "Success Response",
                        value={
                            "message": "Login successful",
                            "user": {
                                "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                                "email": "customer@gmail.com",
                                "role": "CUSTOMER",
                                "full_name": "John Doe",
                            }
                        },
                        response_only=True,
                    ),
                ],
            ),
            400: OpenApiResponse(
                description="Invalid credentials or validation error",
                examples=[
                    OpenApiExample(
                        "Invalid Credentials",
                        value={
                            "non_field_errors": ["Invalid email or password."]
                        },
                        response_only=True,
                    ),
                ],
            ),
        },
        examples=[
            OpenApiExample(
                "Customer Login",
                value={
                    "email": "customer@gmail.com",
                    "password": "Customer@123"
                },
                request_only=True,
            ),
            OpenApiExample(
                "Author Login",
                value={
                    "email": "author@gmail.com",
                    "password": "Author@123"
                },
                request_only=True,
            ),
            OpenApiExample(
                "Admin Login",
                value={
                    "email": "admin@gmail.com",
                    "password": "Admin@123"
                },
                request_only=True,
            ),
        ],
    )
    def post(self, request):

        serializer = LoginSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        user = serializer.validated_data["user"]

        return Response(
            {
                "message": "Login successful",
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "role": user.role,
                    "full_name": user.full_name,
                }
            },
            status=status.HTTP_200_OK
        )