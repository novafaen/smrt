# SMRT framework
Pronounced SMART, is a framework built upon flask, flask-negotiate and requests.

## Purpose
The purpose of this project is to build a framework that will speed up microservice development. However, this project is made for self-educational purpose, so expect the reinvented wheel.

## Usage
Short description how to get started:
1) from `smrt`, import `app` that is the flask application.
2) from `smrt`, import `SMRTApp` that should be extended with your own functionality class.
3) from `smrt`, import `smrt` decorator. This decorator combines flask and flask-negotiate.

## Example
Small example how to use `smrt` to create simple hello world application.

This application will create an app-specific endpoint `POST /hello` and return a greeting
```python
import json
from smrt import app, SMRTApp, smrt, make_response

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
      'version': '1.0.0'
    }
        
  @staticmethod
  def application_name():
    """Use ``SMRTApp`` documentation for ``application_name`` implementation."""
    return 'MyHelloWorldApplication'
  
  def helloName(self, name):
    """Store name of greeter"""
    if name not in self._names:
      self._names.append(name)
      return True  # first time greeted
      
    return False  # person was already greeted before
      
helloWorldApp = HelloWorldApp()  # create application
app.register_application(helloWorldApp)  # and register application with smrt

@smrt('/hello',
      methods=['POST'],
      consumes='application/my.application.name.v1+json',
      produces='application/my.application.greeting.v1+json')
def post_hello():
  data = json.loads(request.data)  # assume correct json format for this example

  firstGreet = helloWorldApp.helloName(data.name)
    
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
Already implemented error handling `smrt` for basic API functionality.
#### Error: Unsupported Media Type (Code 415)
If a endpoint is called, but with wrong (or missing) `Content-Type`, `smrt` will automatically return a `Unsupported Media Type` error.
#### Error: Not Acceptable (406)
If a endpoint is called, but with wrong (or missing) `Accept` header, `smrt` will automatically return a `Not Acceptable` error.
#### Error: Method Not Allowed (405)
If a endpoint is called that does not exist, `smrt` will automatically return a `Method Not Allowed` error. 
Why not `404 Not Found` error when an endpoint does not exist?
`smrt` is created for an API implementation rather than a classic web host. Unknown endpoint should return `Method not Allowed`, while an enpoint that does exist but an ID or resource does not exist should return `Not Found`.

Example (from above):
- `GET /resorce/1337`, resource is spelled incorrectly, no such method exist (i.e. call should return `Method Not Allowed`)
- `GET /resource/1337`, resource with ID 1337 does not exit (i.e. call should return `Not Found`)
#### Error: Bad Gateway (502)
If `smrt` remote call using `request` get `Internal Server Error`, a `Bad Gateway` exception will be raised.
#### Error: Internal Server Error (500)
If a function raise any uncaught exception, `smrt` will return a `Internal Server Error`.

### Routing with Content-Type and Accept
with `@smrt` decorator you can route requests to specific functions.


