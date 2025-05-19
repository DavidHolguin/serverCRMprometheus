from typing import Dict, Any, Optional
from fastapi import Depends, HTTPException, status, Header
from app.db.supabase_client import supabase
import logging
from uuid import UUID

logger = logging.getLogger(__name__)

async def get_current_user(
    authorization: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    Verifica el token de autorización y devuelve el usuario actual.
    
    Este es un método simplificado para la autenticación. En una aplicación real,
    se debería validar el token JWT con Supabase o el proveedor de autenticación.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticación no proporcionado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        # Extraer el token Bearer
        token = authorization.replace("Bearer ", "") if authorization.startswith("Bearer ") else authorization
        
        # Verificar el token con Supabase (esto depende de cómo esté configurada tu autenticación)
        # En este ejemplo, simplemente obtenemos el usuario del token
        # En una implementación real, deberías validar el token con Supabase
        
        # Ejemplo simplificado: obtener el usuario a partir del token
        # Nota: esto es solo un ejemplo, deberías implementar la lógica real de verificación
        try:
            # Intentar obtener el usuario usando el token como ID (solo para ejemplo)
            user_response = supabase.auth.get_user(token)
            user = user_response.user
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Usuario no encontrado o token inválido",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Obtener información adicional del usuario desde la base de datos
            user_id = user.id
            user_data_result = supabase.table("usuarios").select("*").eq("id", user_id).limit(1).execute()
            
            if not user_data_result.data or len(user_data_result.data) == 0:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Usuario no encontrado en la base de datos",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            user_data = user_data_result.data[0]
            
            # Devolver información del usuario
            return {
                "id": user_id,
                "email": user.email,
                "empresa_id": user_data.get("empresa_id"),
                "role": user_data.get("role", "user")
            }
            
        except Exception as e:
            logger.error(f"Error al verificar el token: {str(e)}")
            
            # Para desarrollo, permitir un bypass de autenticación con un token especial
            # NOTA: Esto debe eliminarse en producción
            if token == "development_token":
                # Obtener la primera empresa para testing
                empresa_result = supabase.table("empresas").select("id").limit(1).execute()
                empresa_id = empresa_result.data[0]["id"] if empresa_result.data else None
                
                return {
                    "id": "00000000-0000-0000-0000-000000000000",
                    "email": "dev@example.com",
                    "empresa_id": empresa_id,
                    "role": "admin"
                }
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido o expirado",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en autenticación: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Error de autenticación",
            headers={"WWW-Authenticate": "Bearer"},
        )
