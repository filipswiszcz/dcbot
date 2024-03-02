# dcbot

## features

- AI text assistant
- AI image generator
- music broadcaster


## dependencies
[python-dotenv, discord.py, openai, PyYAML, PyNaCl, async_timeout, pytest, dpytest]


## installation

* use pip to install required packages:


```python
pip3 install -r requirements.txt
```

* add openai api key to .env
* add discord client id to .env
* add discord bot token to .env

### running

```python
python3 main.py
```


### running tests
```python
python3 -m pytest test/
```