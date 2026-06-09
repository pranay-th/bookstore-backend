from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from .serializers import SignupSerializer, LoginSerializer
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse
from apps.core.responses import success_response
from apps.core.serializers import SuccessResponseSerializer, ErrorResponseSerializer


class SignupView(APIView):

    permission_classes = [AllowAny]

    @extend_schema(
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
            201: OpenApiResponse(
                response=SuccessResponseSerializer,
                description="Registration successful",
                examples=[
                    OpenApiExample(
                        "Success Response",
                        value={
                            "status": {
                                "success": True,
                                "code": 201,
                                "message": "Registration successful.",
                            },
                            "data": {
                                "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                                "email": "customer@gmail.com",
                                "role": "CUSTOMER",
                                "full_name": "John Doe",
                            },
                        },
                        response_only=True,
                    ),
                ],
            ),
            400: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="Validation error",
                examples=[
                    OpenApiExample(
                        "Email Already Exists",
                        value={
                            "status": {
                                "success": False,
                                "code": 400,
                                "message": "Validation failed.",
                            },
                            "data": None,
                            "errors": {
                                "email": ["Email already exists."],
                            },
                        },
                        response_only=True,
                    ),
                    OpenApiExample(
                        "Missing Required Fields",
                        value={
                            "status": {
                                "success": False,
                                "code": 400,
                                "message": "Validation failed.",
                            },
                            "data": None,
                            "errors": {
                                "email": ["This field is required."],
                                "password": ["This field is required."],
                            },
                        },
                        response_only=True,
                    ),
                ],
            ),
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

        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        return success_response(
            data={
                "id": str(user.id),
                "email": user.email,
                "role": user.role,
                "full_name": user.full_name,
            },
            message="Registration successful.",
            status_code=201,
        )


class LoginView(APIView):

    permission_classes = [AllowAny]

    @extend_schema(
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
                response=SuccessResponseSerializer,
                description="Login successful",
                examples=[
                    OpenApiExample(
                        "Success Response",
                        value={
                            "status": {
                                "success": True,
                                "code": 200,
                                "message": "Login successful.",
                            },
                            "data": {
                                "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                                "email": "customer@gmail.com",
                                "role": "CUSTOMER",
                                "full_name": "John Doe",
                            },
                        },
                        response_only=True,
                    ),
                ],
            ),
            400: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="Invalid credentials or validation error",
                examples=[
                    OpenApiExample(
                        "Invalid Credentials",
                        value={
                            "status": {
                                "success": False,
                                "code": 400,
                                "message": "Invalid email or password.",
                            },
                            "data": None,
                        },
                        response_only=True,
                    ),
                    OpenApiExample(
                        "Missing Fields",
                        value={
                            "status": {
                                "success": False,
                                "code": 400,
                                "message": "Validation failed.",
                            },
                            "data": None,
                            "errors": {
                                "email": ["This field is required."],
                                "password": ["This field is required."],
                            },
                        },
                        response_only=True,
                    ),
                ],
            ),
            401: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="Account disabled",
                examples=[
                    OpenApiExample(
                        "Account Disabled",
                        value={
                            "status": {
                                "success": False,
                                "code": 401,
                                "message": "Account is disabled.",
                            },
                            "data": None,
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
                    "password": "Customer@123",
                },
                request_only=True,
            ),
            OpenApiExample(
                "Author Login",
                value={
                    "email": "author@gmail.com",
                    "password": "Author@123",
                },
                request_only=True,
            ),
            OpenApiExample(
                "Admin Login",
                value={
                    "email": "admin@gmail.com",
                    "password": "Admin@123",
                },
                request_only=True,
            ),
        ],
    )
    def post(self, request):

        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]

        return success_response(
            data={
                "id": str(user.id),
                "email": user.email,
                "role": user.role,
                "full_name": user.full_name,
            },
            message="Login successful.",
            status_code=200,
        )
