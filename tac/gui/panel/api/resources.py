# -*- coding: utf-8 -*-
from flask_restful import Resource


class HelloWorld(Resource):
    def get(self):
        return {'hello': 'world'}


sandboxes = {}


class Sandbox(Resource):

    def get(self):
        return {}

    def delete(self):
        return {}

    def create(self):
        pass


class SandboxList(Resource):
    pass
