from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text, 
    ForeignKey, func, BigInteger
)
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum
from app.database.database import Base


class OrderStatus(Enum):
    """Статусы заказов"""
    CART = "cart"  # Корзина (черновик)
    PENDING_PAYMENT = "pending_payment"  # 1. Заказ ожидает оплаты
    PAYMENT_RECEIVED = "payment_received"  # 2. Заказ оплачен, ожидает подтверждения
    CONFIRMED = "confirmed"  # 3. Оплата подтверждена, начинаю готовить
    READY = "ready"  # 4. Заказ готов, можно забирать
    COMPLETED = "completed"  # Заказ выполнен (забран/доставлен)
    CANCELLED_BY_CLIENT = "cancelled_by_client"  # 5. Заказ отменен клиентом
    CANCELLED_BY_MASTER = "cancelled_by_master"  # 6. Заказ отменен мастером


class PaymentStatus(Enum):
    """Статусы платежей"""
    PENDING = "pending"  # Ожидает оплаты
    PAID = "paid"  # Оплачен
    CONFIRMED = "confirmed"  # Подтвержден админом
    REJECTED = "rejected"  # Отклонен


class User(Base):
    """Модель пользователя"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Связи
    orders = relationship("Order", back_populates="user")
    
    def __repr__(self):
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, username={self.username})>"


class Category(Base):
    """Модель категории блюд"""
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    image_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Связи
    dishes = relationship("Dish", back_populates="category")
    
    def __repr__(self):
        return f"<Category(id={self.id}, name={self.name})>"


class Dish(Base):
    """Модель блюда"""
    __tablename__ = "dishes"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    image_url = Column(String(500), nullable=True)
    telegram_post_url = Column(String(500), nullable=True)  # Ссылка на пост в канале
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    is_available = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Связи
    category = relationship("Category", back_populates="dishes")
    order_items = relationship("OrderItem", back_populates="dish")
    
    def __repr__(self):
        return f"<Dish(id={self.id}, name={self.name}, price={self.price})>"


class Order(Base):
    """Модель заказа"""
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    total_amount = Column(Float, default=0.0)
    status = Column(String(50), default=OrderStatus.CART.value)
    payment_method = Column(String(20), nullable=True)  # 'card', 'cash'
    payment_screenshot = Column(String(500), nullable=True)
    payment_photo_file_id = Column(String(500), nullable=True)  # file_id фото для повторного просмотра
    notes = Column(Text, nullable=True)
    custom_name = Column(String(255), nullable=True)  # Пользовательское название заказа для повторения
    delivery_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    completed_at = Column(DateTime, nullable=True)
    
    # Связи
    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="order")
    
    def __repr__(self):
        return f"<Order(id={self.id}, user_id={self.user_id}, status={self.status}, total={self.total_amount})>"
    
    @property
    def is_active(self):
        """Проверка, является ли заказ активным"""
        active_statuses = [
            OrderStatus.PENDING_PAYMENT.value,  # 1. Ожидает оплаты
            OrderStatus.PAYMENT_RECEIVED.value,  # 2. Оплачен, ожидает подтверждения
            OrderStatus.CONFIRMED.value,  # 3. Подтвержден, готовится
            OrderStatus.READY.value  # 4. Готов к выдаче
        ]
        return self.status in active_statuses
    
    @property
    def is_completed(self):
        """Проверка, является ли заказ завершенным"""
        completed_statuses = [
            OrderStatus.COMPLETED.value,  # Заказ выполнен
            OrderStatus.CANCELLED_BY_CLIENT.value,  # 5. Отменен клиентом
            OrderStatus.CANCELLED_BY_MASTER.value  # 6. Отменен мастером
        ]
        return self.status in completed_statuses


class OrderItem(Base):
    """Модель позиции заказа"""
    __tablename__ = "order_items"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    dish_id = Column(Integer, ForeignKey("dishes.id"), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    price = Column(Float, nullable=False)  # Цена на момент заказа
    created_at = Column(DateTime, default=func.now())
    
    # Связи
    order = relationship("Order", back_populates="items")
    dish = relationship("Dish", back_populates="order_items")
    
    @property
    def total_price(self):
        return self.quantity * self.price
    
    def __repr__(self):
        return f"<OrderItem(id={self.id}, order_id={self.order_id}, dish_id={self.dish_id}, qty={self.quantity})>"


class Payment(Base):
    """Модель платежа"""
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    amount = Column(Float, nullable=False)
    payment_method = Column(String(50), default="card")  # card, cash
    status = Column(String(50), default=PaymentStatus.PENDING.value)
    screenshot_url = Column(String(500), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
    confirmed_at = Column(DateTime, nullable=True)
    
    # Связи
    order = relationship("Order", back_populates="payments")
    
    def __repr__(self):
        return f"<Payment(id={self.id}, order_id={self.order_id}, amount={self.amount}, status={self.status})>"
