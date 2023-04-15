# -*- coding: utf-8 -*-
"""
/***************************************************************************
 NgToolbox
                                 A QGIS plugin
 NgToolbox API implementation
                             -------------------
        begin                : 2023-02-13
        git sha              : $Format:%H$
        copyright            : (C) 2023 by NextGIS
        email                : info@nextgis.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import os
import uuid
import re
from datetime import datetime
from typing import List, Dict

import requests


API_URL = "https://toolbox.nextgis.com/api"


def is_valid_uuid(value):
    try:
        uuid.UUID(str(value))
        return True
    except ValueError:
        return False


class NgToolgboxConnError(requests.exceptions.ConnectionError):
    '''Any connection exception'''


class NgInputFilename(str):
    def __new__(cls, string):
        if not string[:8] == "storage/" or not is_valid_uuid(string[8:]):
            raise ValueError(
                "Filename must have format like 'storage/ffd294a7-d1d8-45ff-83d7-472e5e0db91e'"
            )
        instance = super().__new__(cls, string.lower())
        return instance


class Input:
    name: str
    title: str
    description: str
    type_: str
    widget: str
    required: bool
    validators: List

    _input_types = {
        "float": float,
        "int": int,
        "string": str,
        "boolean": bool,
        "file": NgInputFilename,
    }
    value = None

    def __init__(self, input_dict):
        self.name = input_dict["name"]
        self.title = input_dict["title"]
        self.description = input_dict["description"]
        self.type_ = self._input_types[input_dict["type"]]
        self.widget = input_dict["widget"]
        self.required = input_dict["required"]
        self.validators = input_dict["validators"]

    def __repr__(self) -> str:
        return str(self.__dict__)

    def set_value(self, value):
        self.value = self.type_(value)


class Inputs:
    inputs: List[Input]

    def __init__(self, inp_list):
        self.inputs = []
        for inp in inp_list:
            self.inputs.append(Input(inp))

    def __iter__(self):
        for inp in self.inputs:
            yield inp

    def __repr__(self) -> str:
        return str(self.inputs)

    def set_value(self, name, value):
        for inp in self.inputs:
            if inp.name == name:
                inp.set_value(value)

    def get_values_for_request(self):
        return {inp.name: inp.value for inp in self}


class Result:
    name: str
    title: str
    value: str

    def __init__(self, res_dict):
        self.name = res_dict["name"]
        self.title = res_dict["title"]
        self.value = res_dict["value"]

    def __repr__(self) -> str:
        return str(self.__dict__)


class Results:
    results: List[Result]

    def __init__(self, res_list):
        self.results = []
        for res in res_list:
            self.results.append(Result(res))

    def __iter__(self):
        for res in self.results:
            yield res

    def __repr__(self) -> str:
        return str(self.results)


class NgToolboxToken:
    token: uuid.UUID

    def __init__(self, token) -> None:
        self.token = uuid.UUID(token)

    def __str__(self):
        return str(self.token)

    def __repr__(self):
        return str(self)

    def get_header(self):
        return {"Authorization": f"Token {self.token}"}


class NgToolboxOrderInputs:
    def __init__(self, inputs) -> None:
        for key in inputs:
            setattr(self, key, inputs[key])

    def __repr__(self) -> str:
        return str(self.__dict__)


class NgToolboxOrderParameters:
    operation_name: str
    inputs: NgToolboxOrderInputs

    def __init__(self, params) -> None:
        self.operation_name = params["operation_name"]
        self.inputs = NgToolboxOrderInputs(params["inputs"])

    def __repr__(self) -> str:
        return str(self.__dict__)


class NgToolboxOrder:
    id: int
    guid: uuid.UUID
    created_at: datetime
    parameters: NgToolboxOrderParameters
    status: str
    priority: int
    tasks: List
    output: List[Input]
    error: str

    def __init__(self, order) -> None:
        self.id = order["id"]
        self.guid = order["guid"]
        self.created_at = order["created_at"]
        self.parameters = NgToolboxOrderParameters(order["parameters"])
        self.status = order["status"]
        self.priority = order["priority"]
        self.tasks = order["tasks"]

    def __repr__(self) -> str:
        return str(self.__dict__)


class NgToolboxOrdersManager:
    api_url: str = API_URL
    token: NgToolboxToken
    orders: List[NgToolboxOrder]

    def __init__(self, token) -> None:
        self.token = NgToolboxToken(token)
        self.orders = self.get_orders()

    def check_conn(f):
        def deco(*args, **kwargs):
            try:
                requests.head(API_URL)
                return f(*args, **kwargs)
            except requests.ConnectionError as e:
                raise NgToolgboxConnError(e)
        return deco

    @check_conn
    def get_orders(self):
        url = f"{self.api_url}/orders/"
        response = requests.get(url, headers=self.token.get_header())
        response.raise_for_status()

        return [NgToolboxOrder(order) for order in response.json()["data"]]

    def update_orders(self):
        self.orders = self.get_orders()

    @check_conn
    def get_status(self, order_id):
        url = f"{self.api_url}/json/status/{order_id}/"
        response = requests.get(url, headers=self.token.get_header())
        return response.json()

    def awfull_filename_search(self, header):
        return [
            i.replace("filename=", "").split("/")[-1]
            for i in header.split(";")
            if "filename=" in i
        ][0].replace('"', "")

    def generate_unique_name(self, name, directory):
        clear_name, ext = os.path.splitext(name)
        files = [
            os.path.splitext(fname)[0]
            for fname in os.listdir(directory)
            if os.path.isfile(os.path.join(directory, fname))
            and os.path.splitext(fname)[1] == ext
        ]
        if re.search("\(\d\)$", clear_name):
            clear_name = clear_name[:-3]

        new_name = clear_name
        id = 1
        if new_name in files:
            while new_name in files:
                new_name = clear_name + "(%d)" % id
                id += 1
        return new_name + ext

    @check_conn
    def download_file(self, url, directory):
        filename = url.split("/")[-1]
        with requests.get(url, headers=self.token.get_header(), stream=True) as r:
            r.raise_for_status()
            if "Content-Disposition" in r.headers:
                filename = self.awfull_filename_search(r.headers["Content-Disposition"])
            filename = self.generate_unique_name(filename, directory)
            file_path = os.path.join(directory, filename)

            with open(file_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

        return file_path

    def get_result(self, result, directory):
        self.download_file(result.value, directory)

    def get_results(self, results, directory):
        for res in results:
            self.download_file(res.value, directory)


class NgToolbox:
    api_url: str = API_URL
    tools: List
    tags: List
    orders_man: NgToolboxOrdersManager
    token: NgToolboxToken

    def __init__(self, locale="en") -> None:
        if locale == "ru":
            self.locale = locale
        else:
            self.locale = "en"
        self.set_locale(locale)
        self.tools = self.get_tools()
        self.tags = self.get_tags()
        self.token = None

    def check_conn(f):
        def deco(*args, **kwargs):
            try:
                requests.head(API_URL)
                return f(*args, **kwargs)
            except requests.ConnectionError as e:
                raise NgToolgboxConnError(e)
        return deco

    def set_current_user(self, token):
        self.token = NgToolboxToken(token)
        self.orders_man = NgToolboxOrdersManager(token)

    @check_conn
    def unset_current_user(self):
        self.token = None
        self.orders_man = None

    def set_locale(self, locale):
        if locale == "ru":
            self.locale = locale
        else:
            self.locale = "en"

    @check_conn
    def get_tools(self) -> List:
        url = f"{self.api_url}/{self.locale}/tools/"
        response = requests.get(url)
        response.raise_for_status()
        tools = response.json()
        return tools["data"]

    @check_conn
    def get_tags(self) -> List:
        url = f"{self.api_url}/{self.locale}/tags/"
        response = requests.get(url)
        response.raise_for_status()
        tags = response.json()
        return tags["data"]

    @check_conn
    def get_tool_inputs(self, tool_id) -> Dict:
        url = f"{self.api_url}/operation/{tool_id}/inputs"
        response = requests.get(url, headers=self.token.get_header())
        response.raise_for_status()
        return Inputs(response.json())

    def refresh_orders(self):
        self.orders_man.update_orders()

    @check_conn
    def upload_file(self, filepath):
        url = f"{self.api_url}/upload/"
        with open(filepath, "rb") as f:
            response = requests.post(url, data=f, headers=self.token.get_header())
        response.raise_for_status()
        return response.text

    @check_conn
    def create_order(self, tool_id, inputs: Inputs):
        json_request = {"operation": tool_id, "inputs": inputs.get_values_for_request()}
        url = f"{self.api_url}/json/execute/"
        response = requests.post(
            url, json=json_request, headers=self.token.get_header()
        )
        response.raise_for_status()
        return response.json()

    def save_results(self, order_id, res_dir):
        status = self.orders_man.get_status(order_id)
        self.orders_man.get_results(Results(status["output"]), res_dir)
