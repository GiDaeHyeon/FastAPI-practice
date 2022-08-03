import os
import jwt
import bcrypt
from functools import wraps
from datetime import datetime, timedelta

from fastapi import Request
from fastapi.responses import JSONResponse

from sqlalchemy import exc, and_
from sqlalchemy.orm import Session
from sqlalchemy.orm import exc as oexc

from model import tables
from model import schemas


def insert_user(user: schemas.UserBase,
                db: Session):
    hashed_password = bcrypt.hashpw(user.password.encode('utf-8'),
                                    bcrypt.gensalt())

    query = tables.Users(name=user.name,
                         email=user.email,
                         profile=user.profile,
                         hashed_password=hashed_password)

    try:
        db.add(query)
        db.commit()
    except exc.IntegrityError:
        return False
    else:
        return user.email


def login(request: Request,
          login_info: schemas.UserLogin,
          db: Session):
    email = login_info.email
    password = login_info.password

    row = db.query(tables.Users.id, tables.Users.email, tables.Users.hashed_password)\
        .filter(tables.Users.email == email).first()

    if row is None:
        return False

    if bcrypt.checkpw(password=password.encode('utf-8'),
                      hashed_password=row.hashed_password.encode('utf-8')):
        payload = {'user_id': row.id,
                   'exp': datetime.utcnow() + timedelta(seconds=60 * 60 * 24)}
        token = jwt.encode(payload, os.environ['JWT_SECRET_KEY'], 'HS256')
        return token, row.id
    else:
        return False


def login_required(func):
    @wraps(func)
    def decorated(request: Request, *args, **kwargs):
        access_token = request.headers.get('Authorization')

        if access_token is None:
            return JSONResponse({'message': 'Unauthorized'},
                                status_code=401)
        else:
            try:
                payload = jwt.decode(access_token, os.environ['JWT_SECRET_KEY'], 'HS256')
            except jwt.InvalidTokenError:
                return JSONResponse({'message': 'Unauthorized'},
                                    status_code=401)
            request.__setattr__('user_id', payload['user_id'])
        return func(request, *args, **kwargs)
    return decorated


def get_user_by_email(new_user: str,
                      db: Session):
    row = db.query(tables.Users).filter(tables.Users.email == new_user).first()

    user = {
        'id': row.id,
        'name': row.name,
        'email': row.email,
        'profile': row.profile
    } if row else None

    return user


def get_user_by_id(user_id: int,
                   db: Session):
    user_check = db.query(tables.Users).filter(tables.Users.id == user_id).first()

    if user_check is None:
        return False
    else:
        return True


def insert_follow(user_id: int,
                  user_id_to_follow: int,
                  db: Session):
    query = tables.UsersFollowList(user_id=user_id,
                                   follow_user_id=user_id_to_follow)

    try:
        db.add(query)
        db.commit()
        return user_id_to_follow
    except exc.IntegrityError:
        return False


def delete_follow(user_id: int,
                  user_id_to_unfollow: int,
                  db: Session):
    query = db.query(tables.UsersFollowList)\
        .filter(and_(tables.UsersFollowList.user_id == user_id,
                     tables.UsersFollowList.follow_user_id == user_id_to_unfollow)).first()
    try:
        db.delete(query)
        db.commit()
    except oexc.UnmappedInstanceError:
        return False
    else:
        return True
