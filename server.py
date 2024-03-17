import json
from sqlite3 import IntegrityError

from aiohttp import web

from models import User, engine, Session

app = web.Application()

#для функии если нужно передать в ссылку id, то нужно добавить в роутер
#/{переменная:\d+}
#а в функцию нужно добавить request.match_info['переменная']
# если это число, то int(request.match_info['переменная'])



async def orm_context(app):
    print("Start")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield
    await engine.dispose()
    print("Finish")

app.cleanup_ctx.append(orm_context)

def get_hhtp_error(error_class, message):
    response = json.dumps({'error': message})
    http_error = error_class(text=response,content_type='application/json')
    return http_error

async def get_user_by_id(session, user_id):
    user = await session.get(User, user_id)
    if user is None:
        raise get_hhtp_error(error_class=web.HTTPFound, message=f'User {user_id} is not found')
    return user

@web.middleware
async def session_middleware(request, handler):
    async with Session() as session:
        request.session = session
        response = await handler(request)
        return response

async def add_user(session, user):
    try:
        session.add(user)
        await session.commit()
    except IntegrityError:
        raise get_hhtp_error(web.HTTPBadRequest, text=f'User with this name already exist')


app.middlewares.append(session_middleware)

class UserView(web.View):

    @property
    def user_id(self):
        return int(self.request.match_info['user_id'])


    @property
    def session(self) -> Session:
        return self.request.session



    async def get(self, author_id: int):
        author = get_user_by_id(self.request.session, author_id)
        return web.json_response(author.create_dict)

    async def post(self):
        data = await self.request.json()
        author = add_user(**data)
        return web.json_response({
            'id': author.id
        })

    async def patch(self, author_id: int):
        data = await self.request.json()
        author = get_user_by_id(self.request.session, author_id)
        for field, value in data.items():
            setattr(author, field, value)
        await add_user(author)
        # print(data)
        return web.json_response({
            'id': author.id
        })

    async def delete(self, author_id: int):
        author = get_user_by_id(self.request.session, author_id)
        await self.session.delete(author)
        await self.session.commit()
        return web.json_response({'Complete': 'OK'})

web.add_routes(
    [web.get('/user/{user_id:\d+}', UserView),
     web.post('/user', UserView),
     web.patch('/user/{user_id:\d+}', UserView),
     web.delete('/user/{user_id:\d+}', UserView)
     ]
)


web.run_app(app)