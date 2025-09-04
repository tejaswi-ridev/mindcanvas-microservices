import grpc
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from .. import auth_pb2, auth_pb2_grpc
from ..models.models import User
from ..core.database import SessionLocal
from ..core.config import settings

class AuthServiceImplementation(auth_pb2_grpc.AuthServiceServicer):

    def ValidateToken(self, request, context):
        db = SessionLocal()
        try:
            # Decode JWT token
            payload = jwt.decode(request.token, settings.secret_key, algorithms=[settings.algorithm])
            user_id = payload.get("sub")

            if user_id is None:
                return auth_pb2.ValidateTokenResponse(
                    valid=False,
                    error="Invalid token payload"
                )

            # Get user from database
            user = db.query(User).filter(User.id == int(user_id)).first()

            if not user:
                return auth_pb2.ValidateTokenResponse(
                    valid=False,
                    error="User not found"
                )

            return auth_pb2.ValidateTokenResponse(
                valid=True,
                user_id=user.id,
                email=user.email
            )

        except JWTError as e:
            return auth_pb2.ValidateTokenResponse(
                valid=False,
                error=str(e)
            )
        finally:
            db.close()

    def CreateUser(self, request, context):
        db = SessionLocal()
        try:
            # Check if user exists
            existing_user = db.query(User).filter(User.email == request.email).first()
            if existing_user:
                return auth_pb2.CreateUserResponse(
                    success=False,
                    error="User already exists"
                )

            # Create new user (this would need password hashing in real implementation)
            from passlib.context import CryptContext
            pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

            new_user = User(
                email=request.email,
                full_name=request.full_name,
                hashed_password=pwd_context.hash(request.password)
            )

            db.add(new_user)
            db.commit()
            db.refresh(new_user)

            return auth_pb2.CreateUserResponse(
                success=True,
                user_id=new_user.id
            )

        except Exception as e:
            db.rollback()
            return auth_pb2.CreateUserResponse(
                success=False,
                error=str(e)
            )
        finally:
            db.close()

    def GetUser(self, request, context):
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == request.user_id).first()

            if not user:
                return auth_pb2.GetUserResponse(
                    error="User not found"
                )

            return auth_pb2.GetUserResponse(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                created_at=user.created_at.isoformat()
            )

        except Exception as e:
            return auth_pb2.GetUserResponse(
                error=str(e)
            )
        finally:
            db.close()
