## Simple 7TV emote import bot.

- Import an emote using a 7TV Url *(f.e https://7tv.app/emotes/01F6NCKMP000052X5637DW2XDY)*
- Custom permissions using `/permissions`
> *If you want to use discord's built-in permissions manager from Integrations menu, just set every command default permission to `True` in config.py*
- Basic configuration in `config.py`

### To self-host.
1. Create an app on https://discord.dev
2. Install python 3.11+ (https://python.org)
   - Also consider creating a virtual environment (https://docs.python.org/3/library/venv.html)
3. Install requirements `pip install -r -U requirements.txt`
4. Create a file named `.env` and put your apps token here, like shown in `.env.example` -> *TOKEN=token*
5. Check configs in config.py (you might wanna edit default permissions for commands, i guess)
6. Run main.py `python main.py`

### Or add hosted version using -> https://discord.com/oauth2/authorize?client_id=851205565031645204
