from fastapi import FastAPI, Depends, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy.orm import Session

from model.conn import create_engine_session, Base
from model import schemas

from service import user_service, tweet_service

engine, session = create_engine_session()


def get_db():
    db = session()
    try:
        yield db
    finally:
        db.close()


def create_app(engine_):
    app_ = FastAPI()

    Base.metadata.create_all(bind=engine_)

    origins = [
        "http://localhost:5000",
        "http://127.0.0.1:5000"
    ]

    app_.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return app_


app = create_app(engine)


@app.get('/ping', tags=['Health Check'])
def ping():
    content = {'message': 'pong'}
    return JSONResponse(content=content, status_code=200)


@app.put('/sign-up', tags=['User'])
def sign_up(new_user: schemas.UserBase,
            db: Session = Depends(get_db)):

    print(new_user)

    new_user = user_service.insert_user(new_user, db)

    if not new_user:
        return JSONResponse(content=f'Duplicate Entry {new_user}',
                            status_code=400)
    new_user_info = user_service.get_user_by_email(new_user, db)

    if not new_user_info:
        return JSONResponse(content='Unknown Error',
                            status_code=400)

    return JSONResponse(content=new_user_info, status_code=200)


@app.post('/login', tags=['User'])
def login(request: Request,
          user: schemas.UserLogin,
          db: Session = Depends(get_db)):
    try:
        access_token, user_id = user_service.login(request, user, db)
    except TypeError:
        return JSONResponse(content={'detail': 'Wrong Email or Password'},
                            status_code=400)

    if not access_token:
        return JSONResponse(content={'detail': 'Wrong Email or Password'},
                            status_code=400)
    else:
        return JSONResponse(content={'message': 'Login Success!',
                                     'access_token': access_token},
                            status_code=200)


@app.put('/tweet', tags=['Tweet'])
@user_service.login_required
def tweet(request: Request,
          new_tweet: schemas.TweetBase,
          db: Session = Depends(get_db)):
    tweet_content = new_tweet.tweet
    user_id = request.headers.get('user_id')

    if len(tweet_content) > 300:
        return HTTPException(400, detail='Cannot Over 300')

    content = tweet_service.insert_tweet(tweet_content, user_id, db)

    if content is None:
        return HTTPException(400, detail='Unknown Error')

    return JSONResponse(content=content, status_code=200)


@app.put('/follow', tags=['User'])
@user_service.login_required
def follow(request: Request,
           user_follow: schemas.Follow,
           db: Session = Depends(get_db)):
    user_id = request.user_id
    follow_info = [user_id, user_follow.user_id_to_follow]

    for info in follow_info:
        if not user_service.get_user_by_id(info, db):
            return JSONResponse(content={'detail': 'No User'},
                                status_code=400)

    if not user_service.insert_follow(follow_info[0], follow_info[1], db):
        return JSONResponse(content={'detail': 'Already Following'}, status_code=400)
    else:
        return JSONResponse(content={'user_id': follow_info[0],
                                     'user_id_to_follow': follow_info[1]}, status_code=200)


@app.delete('/unfollow', tags=['User'])
@user_service.login_required
def unfollow(request: Request,
             user_unfollow: schemas.Follow,
             db: Session = Depends(get_db)):
    user_id = request.user_id
    user_id_to_unfollow = user_unfollow.user_id_to_follow

    if not user_service.delete_follow(user_id, user_id_to_unfollow, db):
        return JSONResponse(content={'detail': 'Invalid User'},
                            status_code=400)
    else:
        return JSONResponse(content={'user_id': user_id,
                                     'user_id_to_unfollow': user_id_to_unfollow},
                            status_code=200)


@app.get('/timeline', tags=['Tweet'])
@user_service.login_required
def timeline(request: Request,
             db: Session = Depends(get_db)):
    user_id = request.user_id
    tweets = tweet_service.get_timeline(user_id, db)
    return JSONResponse(content=tweets, status_code=200) if tweets is not None \
        else JSONResponse(content={'detail': 'No Contents'}, status_code=400)
