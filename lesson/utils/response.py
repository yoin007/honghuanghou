# _*_ coding: utf-8 _*_
# 统一响应格式工具

from typing import Any, Optional
from fastapi.responses import JSONResponse
from fastapi import Request, HTTPException
from enum import Enum


class ResponseCode(int, Enum):
    """响应状态码"""
    SUCCESS = 200
    CREATED = 201
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    INTERNAL_SERVER_ERROR = 500


class ResponseModel:
    """统一响应模型"""

    @staticmethod
    def success(data: Any = None, message: str = "操作成功", code: int = ResponseCode.SUCCESS) -> JSONResponse:
        """
        成功响应

        Args:
            data: 响应数据
            message: 响应消息
            code: 状态码

        Returns:
            JSONResponse
        """
        content = {
            "code": code,
            "message": message,
            "data": data
        }
        return JSONResponse(content=content, status_code=code)

    @staticmethod
    def error(message: str = "操作失败", code: int = ResponseCode.INTERNAL_SERVER_ERROR, details: Any = None) -> JSONResponse:
        """
        错误响应

        Args:
            message: 错误消息
            code: 错误状态码
            details: 详细错误信息

        Returns:
            JSONResponse
        """
        content = {
            "code": code,
            "message": message,
            "data": None
        }
        if details:
            content["details"] = details
        return JSONResponse(content=content, status_code=code)

    @staticmethod
    def paginate(data: list, page: int = 1, page_size: int = 20, total: int = 0, message: str = "操作成功") -> JSONResponse:
        """
        分页响应

        Args:
            data: 数据列表
            page: 当前页码
            page_size: 每页数量
            total: 总数
            message: 响应消息

        Returns:
            JSONResponse
        """
        content = {
            "code": ResponseCode.SUCCESS,
            "message": message,
            "data": {
                "items": data,
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": (total + page_size - 1) // page_size if page_size > 0 else 0
            }
        }
        return JSONResponse(content=content)


# 便捷函数
def success_response(data: Any = None, message: str = "操作成功"):
    """成功响应便捷函数"""
    return ResponseModel.success(data, message)


def error_response(message: str = "操作失败", code: int = ResponseCode.INTERNAL_SERVER_ERROR):
    """错误响应便捷函数"""
    return ResponseModel.error(message, code)


def paginate_response(data: list, page: int = 1, page_size: int = 20, total: int = 0):
    """分页响应便捷函数"""
    return ResponseModel.paginate(data, page, page_size, total)


class APIException(HTTPException):
    """自定义 API 异常"""

    def __init__(self, status_code: int = 500, detail: str = "内部服务器错误", code: int = None):
        self.detail = detail
        self.status_code = status_code
        self.code = code or status_code
        super().__init__(status_code=status_code, detail=detail)


class NotFoundException(APIException):
    """资源不存在异常"""

    def __init__(self, detail: str = "资源不存在"):
        super().__init__(status_code=404, detail=detail, code=404)


class UnauthorizedException(APIException):
    """未授权异常"""

    def __init__(self, detail: str = "未授权"):
        super().__init__(status_code=401, detail=detail, code=401)


class ForbiddenException(APIException):
    """禁止访问异常"""

    def __init__(self, detail: str = "禁止访问"):
        super().__init__(status_code=403, detail=detail, code=403)


class BadRequestException(APIException):
    """请求参数错误异常"""

    def __init__(self, detail: str = "请求参数错误"):
        super().__init__(status_code=400, detail=detail, code=400)
