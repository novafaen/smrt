# SMRT framework
Pronounced SMART, is a microservice framework built upon; flask, flask-negotiate and requests.

## Purpose
The purpose of this project is to build a framework that will speed up (my) microservice development while learning Python programming language. This project is made for self-educational purpose, expect the wheel re-invented!

## Usage
Short description how to get started:
1) from `smrt`, import `app` that is the flask application.
2) from `smrt`, import `SMRTApp` that should be extended with your own functionality class.
3) from `smrt`, import `smrt` decorator. This decorator combines flask and flask-negotiate.

## Example
Small example how to use `smrt` to create simple hello world application. Below is an example application that exposes endpoint `POST /hello` that returns a greeting, and if the name have been greeted before.

### Imports
Imported on seperate rows just to clarify why you need to import these. These are the bare minimum you need from `smrt` to get started.
```python
from smrt import app  # SMRT class that extend flask app.
from smrt import SMRTApp  # class to be extended with application specific functionality.
from smrt import smrt  # routing decorator.
from smrt import make_response  # creates correct response type to be returned to caller.
from smrt import get, put, post  # wrappers around requests to hande exceptions in a smrt way.
```

### Extending SMRTApp
To create your own application, you need to extend `SMRTApp` class. the functions `status` and `application_name` are the two only mandatory functions to implement.
```python
class HelloWorldApp(SMRTApp):
  """My first ``SMRTApp``, expect great things to come."""
  
  def __init__(self):
    """Create and initiate ````HelloWorldApp`` application."""
    SMRTApp.__init__(self)
        
    self._names = []
        
  def status(self):
    """Use ``SMRTApp`` documentation for ``status`` implementation."""
    return {
      'name': self.application_name(),
      'status': 'OK',  # hello world is always ok :)
      'version': self.version()
    }
    
  @staticmethod
  def version():
    """Use ``SMRTApp`` documentation for ``version`` implementation."""
    return '1.0.0'

  @staticmethod
  def application_name():
    """Use ``SMRTApp`` documentation for ``application_name`` implementation."""
    return 'MyHelloWorldApplication'
  
  def helloName(self, name):
    """Store name of greeter
    
    :param name: `String` name of greeter
    :returns: `True` if first time name is greeted, otherwise `False`
    """
    if name not in self._names:
      self._names.append(name)
      return True  # first time greeted
      
    return False  # person was already greeted before
```

### Register application with SMRT
```python
helloWorldApp = HelloWorldApp()  # create application
app.register_application(helloWorldApp)  # and register application with smrt
```

### Create endpoint
```python
@smrt('/hello',
      methods=['POST'],
      consumes='application/my.application.name.v1+json',
      produces='application/my.application.greeting.v1+json')
def post_hello():
  data = json.loads(request.data)  # assume correct json format for this example

  firstGreet = helloWorldApp.helloName(data['name'])
    
  body = {
    "message": "Hello %s, how are you?" % name,
    "youFirstTimeHere": firstGreet
  }
    
  response = make_response(jsonify(body), 200)
  response.headers['Content-Type'] = 'application/my.application.greeting.v1+json'
  return response
```

## Features

### Error handling
`smrt` provide basic error handling for basic API functionality.

#### Method Not Allowed (400)
Thrown automatically if endpoint called with correct `Content-Type`, but `json` is invalid or does not conform to schema.

#### Method Not Allowed (405)
If a endpoint is called that does not exist, `smrt` will automatically return a `Method Not Allowed` error. 

Why not `404 Not Found` error when an endpoint does not exist?

Ok, hear me out: `smrt` is created for an API implementation rather than a classic web host. Unknown endpoint should return `Method not Allowed`, while an enpoint that does exist but an ID or resource does not exist should return `Not Found`.

Example:
- `GET /resorce/1337`, resource is spelled incorrectly, no such method exist (i.e. call should return `Method Not Allowed`)
- `GET /resource/1337`, resource with ID 1337 does not exit (i.e. call should return `Not Found`)

#### Not Acceptable (406)
If a endpoint is called, but with wrong (or missing) `Accept` header, `smrt` will automatically return a `Not Acceptable` error.

#### Unsupported Media Type (Code 415)
If a endpoint is called, but with wrong (or missing) `Content-Type`, `smrt` will automatically return a `Unsupported Media Type` error.

#### Internal Server Error (500)
If a function raise any uncaught exception, `smrt` will return a `Internal Server Error`.

#### Bad Gateway (502)
If `smrt` remote call using `request` get `Internal Server Error`, a `Bad Gateway` exception will be raised.

### Routing with Content-Type and Accept
with `@smrt` decorator you can route requests to specific functions. See `Flask-Negotiate` documentation how to use this.

Why not just use `Flask` and `Flask-Negotiate`?

Ok, hear me out: `smrt` combines these to automatically return `Method Not Allowed` or `Not Acceptable` instead of `Not Found` that you would get without `smrt`. This feature might already exist, maybe, but since this project is for self education I re-invented the wheel :)

Example:
```python
@smrt('/enpoint',  # endpoint, just as @app.route from flask
      methods=['GET', 'POST'],  # methods, just as @app.route from flask.
      consumes='application/my.application.input.v1+json',  # content-type, just like @consumes from flask-negotiate.
      produces='application/my.application.output.v1+json')  # accept, just like @produces from flask-negotiate.
```

### Status endpoint
`smrt` will come with one pre-defined endpoint called `/status`. This will return `smrt` state as well call counters and status from your application (that extends `status` function from `SMRTApp` interface).

Example output:
```json
{
  "smrt": {
      "smrt_version": "0.0.1",
      "app_loaded": true,
      "uptime": 468163980
  },
  "application": {
    "name": "MyHelloWorldApplication",
    "status": "OK",
    "version": "1.0.3"
  },
  "server_time": 946731723,
  "status": {
    "amount_successful": 23,
    "amount_warning": 0,
    "amount_error": 0,
    "amount_bad": 8,
    "amount_total": 31
  }
}
```

## SMRTApp interface
An application that you want to use with `smrt` framework need to implement `SMRTApp` interface (extend the class). Required functions to implement is listed below.

### status
Function should return a dictionary containing name, status and version.

Example:
```json
def status(self):
  {
    "name": "MyHelloWorldApplication",
    "status": "OK",
    "version": "1.0.3"
  }
```
### application_name (@staticmethod)
Function should return a string containing application name.

Example:
```python
@staticmethod
def application_name():
  return "MyHelloWorldApplication"
```

### version (@staticmethod)
Function should return a string representation of application version.

Example:
```python
@staticmethod
def version():
  return "1.0.3"
```

## Limitations
Don't get me started, `smrt` is basically limitations only :)
