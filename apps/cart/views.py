"""
cart/views.py

The authenticated user's shopping cart.

Endpoints (all scoped to request.user — a user can only ever touch their own cart):
  GET    /api/cart/                     Retrieve the current user's cart
  DELETE /api/cart/clear/               Empty the cart
  POST   /api/cart/add/                 Add a book (or increment if already present)
  POST   /api/cart/items/<id>/increment/   Increment a line item by 1
  POST   /api/cart/items/<id>/decrement/   Decrement a line item by 1 (removes at 0)
  PATCH  /api/cart/items/<id>/quantity/    Set a line item's absolute quantity
  DELETE /api/cart/items/<id>/remove/       Remove a line item entirely
"""
import logging

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet

from apps.core.responses import error_response, success_response
from apps.core.serializers import ErrorResponseSerializer, SuccessResponseSerializer

from .models import Cart, CartItem
from .serializers import (
    AddToCartSerializer,
    CartItemSerializer,
    CartSerializer,
    UpdateQuantitySerializer,
)
from apps.books.models import Book

logger = logging.getLogger(__name__)


class CartViewSet(GenericViewSet):
    """
    Manage the authenticated user's cart.

    The cart is created lazily on first access, so every user effectively
    always has a cart. All actions are owner-scoped.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = CartSerializer
    # Declared for schema generation + router basename inference; all real
    # access goes through the owner-scoped helpers below.
    queryset = CartItem.objects.none()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _get_cart(self):
        """Return (creating if needed) the current user's cart."""
        cart, _ = Cart.objects.get_or_create(user=self.request.user)
        return cart

    def _cart_payload(self, cart):
        """Re-fetch with prefetch and serialize the whole cart."""
        cart = (
            Cart.objects.filter(pk=cart.pk)
            .prefetch_related('items__book')
            .first()
        )
        return CartSerializer(cart).data

    # ------------------------------------------------------------------
    # RETRIEVE — GET /api/cart/
    # ------------------------------------------------------------------
    @extend_schema(
        summary="Get the current user's cart",
        description="Returns the authenticated user's cart with all line items and computed totals.",
        responses={
            200: OpenApiResponse(
                response=SuccessResponseSerializer,
                description="Cart retrieved",
            ),
        },
    )
    def list(self, request, *args, **kwargs):
        cart = self._get_cart()
        return success_response(
            data=self._cart_payload(cart),
            message="Cart retrieved.",
        )

    # ------------------------------------------------------------------
    # ADD — POST /api/cart/add/
    # ------------------------------------------------------------------
    @extend_schema(
        summary="Add a book to the cart",
        description=(
            "Adds the given book to the cart. If the book is already in the cart, "
            "its quantity is increased by the requested amount. The unit price is "
            "snapshotted from the book the first time it is added."
        ),
        request=AddToCartSerializer,
        responses={
            200: OpenApiResponse(response=SuccessResponseSerializer, description="Item added"),
            400: OpenApiResponse(response=ErrorResponseSerializer, description="Validation error"),
            404: OpenApiResponse(response=ErrorResponseSerializer, description="Book not found"),
        },
        examples=[
            OpenApiExample(
                "Add one copy",
                value={"book_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6", "quantity": 1},
                request_only=True,
            ),
        ],
    )
    @action(detail=False, methods=["post"])
    def add(self, request):
        serializer = AddToCartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        book_id = serializer.validated_data["book_id"]
        quantity = serializer.validated_data["quantity"]

        book = Book.objects.filter(id=book_id, is_active=True).first()
        if book is None:
            return error_response("Book not found.", status_code=404)

        if book.stock <= 0:
            return error_response("This book is out of stock.", status_code=400)

        cart = self._get_cart()
        item, created = CartItem.objects.get_or_create(
            cart=cart,
            book=book,
            defaults={"quantity": quantity, "unit_price": book.price},
        )
        if not created:
            item.quantity += quantity
            item.save(update_fields=["quantity", "updated_at"])

        logger.info(
            "Cart add | user_id=%s book_id=%s qty=%s (created=%s)",
            request.user.id, book.id, quantity, created,
        )
        return success_response(
            data=self._cart_payload(cart),
            message="Book added to cart.",
            status_code=200,
        )

    # ------------------------------------------------------------------
    # CLEAR — DELETE /api/cart/clear/
    # ------------------------------------------------------------------
    @extend_schema(
        summary="Clear the cart",
        description="Removes every item from the authenticated user's cart.",
        responses={200: OpenApiResponse(response=SuccessResponseSerializer, description="Cart cleared")},
    )
    @action(detail=False, methods=["delete"])
    def clear(self, request):
        cart = self._get_cart()
        deleted, _ = cart.items.all().delete()
        logger.info("Cart cleared | user_id=%s removed=%s", request.user.id, deleted)
        return success_response(
            data=self._cart_payload(cart),
            message="Cart cleared.",
        )

    # ------------------------------------------------------------------
    # Item helpers
    # ------------------------------------------------------------------
    def _get_item(self, pk):
        """Fetch a cart item that belongs to the current user, or 404."""
        return get_object_or_404(
            CartItem.objects.select_related('book', 'cart'),
            pk=pk,
            cart__user=self.request.user,
        )

    # ------------------------------------------------------------------
    # INCREMENT — POST /api/cart/items/<id>/increment/
    # ------------------------------------------------------------------
    @extend_schema(
        summary="Increment a cart item",
        description="Increases the quantity of a single cart item by 1.",
        request=None,
        responses={
            200: OpenApiResponse(response=SuccessResponseSerializer, description="Item incremented"),
            404: OpenApiResponse(response=ErrorResponseSerializer, description="Item not found"),
        },
    )
    @action(detail=True, methods=["post"], url_path="increment")
    def increment(self, request, pk=None):
        item = self._get_item(pk)
        item.quantity += 1
        item.save(update_fields=["quantity", "updated_at"])
        logger.info("Cart increment | user_id=%s item_id=%s qty=%s", request.user.id, item.id, item.quantity)
        return success_response(
            data=self._cart_payload(item.cart),
            message="Item quantity increased.",
        )

    # ------------------------------------------------------------------
    # DECREMENT — POST /api/cart/items/<id>/decrement/
    # ------------------------------------------------------------------
    @extend_schema(
        summary="Decrement a cart item",
        description="Decreases the quantity by 1. When the quantity reaches 0, the item is removed.",
        request=None,
        responses={
            200: OpenApiResponse(response=SuccessResponseSerializer, description="Item decremented or removed"),
            404: OpenApiResponse(response=ErrorResponseSerializer, description="Item not found"),
        },
    )
    @action(detail=True, methods=["post"], url_path="decrement")
    def decrement(self, request, pk=None):
        item = self._get_item(pk)
        cart = item.cart
        if item.quantity <= 1:
            item.delete()
            logger.info("Cart decrement->remove | user_id=%s item_id=%s", request.user.id, pk)
            return success_response(
                data=self._cart_payload(cart),
                message="Item removed from cart.",
            )
        item.quantity -= 1
        item.save(update_fields=["quantity", "updated_at"])
        logger.info("Cart decrement | user_id=%s item_id=%s qty=%s", request.user.id, item.id, item.quantity)
        return success_response(
            data=self._cart_payload(cart),
            message="Item quantity decreased.",
        )

    # ------------------------------------------------------------------
    # SET QUANTITY — PATCH /api/cart/items/<id>/quantity/
    # ------------------------------------------------------------------
    @extend_schema(
        summary="Set a cart item's quantity",
        description="Sets the absolute quantity of a cart item (minimum 1).",
        request=UpdateQuantitySerializer,
        responses={
            200: OpenApiResponse(response=SuccessResponseSerializer, description="Quantity updated"),
            400: OpenApiResponse(response=ErrorResponseSerializer, description="Validation error"),
            404: OpenApiResponse(response=ErrorResponseSerializer, description="Item not found"),
        },
        examples=[OpenApiExample("Set quantity to 3", value={"quantity": 3}, request_only=True)],
    )
    @action(detail=True, methods=["patch"], url_path="quantity")
    def set_quantity(self, request, pk=None):
        item = self._get_item(pk)
        serializer = UpdateQuantitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item.quantity = serializer.validated_data["quantity"]
        item.save(update_fields=["quantity", "updated_at"])
        logger.info("Cart set-qty | user_id=%s item_id=%s qty=%s", request.user.id, item.id, item.quantity)
        return success_response(
            data=self._cart_payload(item.cart),
            message="Item quantity updated.",
        )

    # ------------------------------------------------------------------
    # REMOVE — DELETE /api/cart/items/<id>/remove/
    # ------------------------------------------------------------------
    @extend_schema(
        summary="Remove a cart item",
        description="Removes a single line item from the cart entirely.",
        responses={
            200: OpenApiResponse(response=SuccessResponseSerializer, description="Item removed"),
            404: OpenApiResponse(response=ErrorResponseSerializer, description="Item not found"),
        },
    )
    @action(detail=True, methods=["delete"], url_path="remove")
    def remove(self, request, pk=None):
        item = self._get_item(pk)
        cart = item.cart
        item.delete()
        logger.info("Cart remove | user_id=%s item_id=%s", request.user.id, pk)
        return success_response(
            data=self._cart_payload(cart),
            message="Item removed from cart.",
        )
