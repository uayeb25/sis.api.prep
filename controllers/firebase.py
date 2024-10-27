import os
import requests
import json
import logging
import traceback
import random

from dotenv import load_dotenv
from fastapi import HTTPException

from models.UserRegister import UserRegister
from models.UserLogin import UserLogin

import firebase_admin
from firebase_admin import credentials, auth as firebase_auth

from utils.database import fetch_query_as_json
from utils.security import create_jwt_token


# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inicializar la app de Firebase Admin
cred = credentials.Certificate("secrets/firebase-secret.json")
firebase_admin.initialize_app(cred)


load_dotenv()


async def register_user_firebase(user: UserRegister):
    user_record = {}
    try:
        # Crear usuario en Firebase Authentication
        user_record = firebase_auth.create_user(
            email=user.email,
            password=user.password
        )

    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=400,
            detail=f"Error al registrar usuario: {e}"
        )

    query = f" exec exampleprep.create_user @email = '{user.email}', @firstname = '{user.firstname}', @lastname = '{user.lastname}'"
    result = {}
    try:

        result_json = await fetch_query_as_json(query, is_procedure=True)
        result = json.loads(result_json)[0]

        return result

    except Exception as e:
        firebase_auth.delete_user(user_record.uid)
        raise HTTPException(status_code=500, detail=str(e))


async def login_user_firebase(user: UserLogin):
    try:
        # Autenticar usuario con Firebase Authentication usando la API REST
        api_key = os.getenv("FIREBASE_API_KEY")  # Reemplaza esto con tu apiKey de Firebase
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"
        payload = {
            "email": user.email,
            "password": user.password,
            "returnSecureToken": True
        }
        response = requests.post(url, json=payload)
        response_data = response.json()

        if "error" in response_data:
            raise HTTPException(
                status_code=400,
                detail=f"Error al autenticar usuario: {response_data['error']['message']}"
            )

        query = f"""select 
                        email
                        , firstname
                        , lastname
                        , active
                    from [exampleprep].[users]
                    where email = '{ user.email }'
                    """

        try:
            result_json = await fetch_query_as_json(query)
            result_dict = json.loads(result_json)
            return {
                "message": "Usuario autenticado exitosamente",
                "idToken": create_jwt_token(
                    result_dict[0]["firstname"],
                    result_dict[0]["lastname"],
                    user.email,
                    result_dict[0]["active"]
                )
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        error_detail = {
            "type": type(e).__name__,
            "message": str(e),
            "traceback": traceback.format_exc()
        }
        raise HTTPException(
            status_code=400,
            detail=f"Error al login usuario: {error_detail}"
        )
