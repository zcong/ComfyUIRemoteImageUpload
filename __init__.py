"""
ComfyUI自定义节点：远程图片上传
将图片上传到远程服务器
"""

import io
import os
import requests
import tempfile
import time
from pathlib import Path

import numpy as np
from PIL import Image
from comfy_api.latest._input_impl.video_types import (
    VideoFromComponents,
    VideoFromFile,
)

VIDEO_MIME_TYPES = {
    "mp4": "video/mp4",
    "mov": "video/quicktime",
    "mkv": "video/x-matroska",
    "webm": "video/webm",
    "avi": "video/x-msvideo",
}


def build_upload_filename(ext):
    """生成上传占位文件名，正式文件名由服务端统一分配。"""
    return f"upload.{ext.lower()}"


def detect_video_mime_type(filename_or_path):
    """根据文件扩展名检测视频 MIME 类型。"""
    if not filename_or_path or "." not in str(filename_or_path):
        return "video/mp4"

    ext = str(filename_or_path).rsplit(".", 1)[1].lower()
    return VIDEO_MIME_TYPES.get(ext, "video/mp4")


def build_video_upload_name(path_or_name=None, default_ext="mp4"):
    """为视频生成上传占位文件名，保留扩展名供服务端识别。"""
    if path_or_name:
        ext = Path(str(path_or_name)).suffix.lower().lstrip(".") or default_ext
    else:
        ext = default_ext
    return build_upload_filename(ext)


class ComfyUIRemoteVideoUpload:
    """
    Upload VIDEO input to remote server
    """
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "video": ("VIDEO",),
                "upload_url": ("STRING", {
                    "default": "http://127.0.0.1:65360/upload_video"
                }),
                "api_key": ("STRING", {
                    "default": ""
                }),
                "timeout_seconds": ("INT", {
                    "default": 300,
                    "min": 30,
                    "max": 3600
                }),
            }
        }

    RETURN_TYPES = ()
    FUNCTION = "upload"
    OUTPUT_NODE = True
    CATEGORY = "utils/network"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        # 禁用缓存，确保每次都会执行上传
        return float("nan")

    def _get_video_bytes(self, video):
        """
        Returns:
            (video_bytes: bytes, filename: str, mime_type: str)
        """

        # -----------------------------
        # 1. VideoFromComponents
        # -----------------------------
        if isinstance(video, VideoFromComponents):
            ext = "mp4"

            with tempfile.NamedTemporaryFile(suffix=f".{ext}") as tmp: 
                video.save_to(tmp.name)
                tmp.seek(0)
                data = tmp.read()

            filename = build_video_upload_name(default_ext=ext)
            return data, filename, detect_video_mime_type(filename)

        # -----------------------------
        # 2. VideoFromFile
        # -----------------------------
        if isinstance(video, VideoFromFile):

            # 2.1 优先直接用已有文件路径（零拷贝）
            path = getattr(video, "path", None)
            if isinstance(path, str) and os.path.exists(path):
                filename = build_video_upload_name(path)
                with open(path, "rb") as f:
                    return f.read(), filename, detect_video_mime_type(filename)

            # 2.2 fallback：用 save_to（内存或临时文件）
            buffer = io.BytesIO()
            video.save_to(buffer)

            buffer.seek(0)
            video_bytes = buffer.read()

            filename = build_video_upload_name(default_ext=video.get_container_format() or "mp4")

            return video_bytes, filename, detect_video_mime_type(filename)

        # -----------------------------
        # 3. 其他兼容输入（可选）
        # -----------------------------
        if isinstance(video, (str, Path)):
            path = str(video)
            if not os.path.exists(path):
                raise RuntimeError(f"Video path does not exist: {path}")

            filename = build_video_upload_name(path)
            with open(path, "rb") as f:
                return f.read(), filename, detect_video_mime_type(filename)

        if hasattr(video, "read"):
            data = video.read()
            if hasattr(video, "seek"):
                video.seek(0)

            original_name = os.path.basename(getattr(video, "name", "video.mp4"))
            filename = build_video_upload_name(original_name)

            return data, filename, detect_video_mime_type(filename)

        # -----------------------------
        # 4. 不支持的类型
        # -----------------------------
        raise RuntimeError(
            f"Unsupported VIDEO input type: {type(video)}"
        )

    def upload(self, video, upload_url, api_key, timeout_seconds):
        """
        上传视频到远程服务器
        
        Args:
            video: VIDEO 输入（支持多种格式）
            upload_url: 上传服务器地址
            api_key: API 密钥
            timeout_seconds: 超时时间（秒）
        
        Returns:
            空元组（无输出）
        """
        try:
            # 获取视频字节内容
            video_bytes, filename, mime_type = self._get_video_bytes(video)
            
            if not video_bytes:
                raise RuntimeError("Failed to extract video bytes from VIDEO input")
            
            headers = {
                "X-API-KEY": api_key
            }
            
            # 使用 BytesIO 包装字节数据
            video_file = io.BytesIO(video_bytes)
            files = {
                "file": (filename, video_file, mime_type)
            }
            
            try:
                start = time.time()
                resp = requests.post(
                    upload_url,
                    headers=headers,
                    files=files,
                    timeout=timeout_seconds
                )
                cost = time.time() - start
                
            except requests.exceptions.Timeout:
                raise RuntimeError(
                    f"Video upload timeout after {timeout_seconds}s"
                )
            
            except Exception as e:
                raise RuntimeError(f"Video upload failed: {e}")
            
            if resp.status_code != 200:
                raise RuntimeError(
                    f"Upload failed [{resp.status_code}]: {resp.text}"
                )
            
            result = resp.json()
            saved_filename = result.get("filename", filename)
            print(
                f"[VideoUpload] OK: {saved_filename} ({len(video_bytes)} bytes), cost={cost:.2f}s"
            )
            
        except RuntimeError:
            raise  # 重新抛出 RuntimeError
        except Exception as e:
            raise RuntimeError(f"Video upload error: {e}")
        
        return ()

class RemoteImageUpload:
    """
    ComfyUI自定义节点：远程图片上传节点
    接收图片输入和秘钥，将图片上传到远程服务器
    """
    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")

    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "api_key": ("STRING", {
                    "multiline": False,
                    "default": ""
                }),
                "server_url": ("STRING", {
                    "multiline": False,
                    "default": "http://localhost:65360/upload"
                }),
            }
        }
    
    RETURN_TYPES = ()
    FUNCTION = "upload_image"
    CATEGORY = "image/remote"
    OUTPUT_NODE = True  # 这是一个输出节点，不返回数据

    def _build_image_filename(self):
        """生成上传占位文件名，正式文件名由服务端统一分配。"""
        return build_upload_filename("png")
    
    def upload_image(self, image, api_key, server_url):
        """
        上传图片到远程服务器
        
        Args:
            image: ComfyUI的IMAGE类型（torch.Tensor格式，形状为[batch, height, width, channels]）
            api_key: 用户输入的API秘钥
            server_url: 服务器上传地址
        
        Returns:
            空元组（无输出）
        """
        try:
            # 验证输入
            if not api_key or not api_key.strip():
                print(f"[RemoteImageUpload] 错误: API秘钥不能为空")
                return ()
            
            if not server_url or not server_url.strip():
                print(f"[RemoteImageUpload] 错误: 服务器地址不能为空")
                return ()
            
            # 将torch.Tensor转换为PIL Image
            # ComfyUI的IMAGE格式: [batch, height, width, channels]，值范围0-1
            if len(image.shape) == 4:
                # 取第一张图片（如果有batch维度）
                img_tensor = image[0]
            else:
                img_tensor = image
            
            # 转换为numpy数组并缩放到0-255范围
            img_np = (img_tensor.cpu().numpy() * 255.0).astype(np.uint8)
            
            # 转换为PIL Image
            pil_image = Image.fromarray(img_np)
            
            # 将PIL Image转换为字节流（PNG格式）
            buf = io.BytesIO()
            pil_image.save(buf, format="PNG")
            buf.seek(0)
            
            # 准备HTTP请求
            headers = {
                "X-API-KEY": api_key.strip()
            }

            filename = self._build_image_filename()
            
            files = {
                "file": (filename, buf, "image/png")
            }
            
            # 发送POST请求
            print(f"[RemoteImageUpload] 正在上传图片到 {server_url}...")
            response = requests.post(
                server_url.strip(),
                headers=headers,
                files=files,
                timeout=30
            )
            
            # 处理响应
            if response.status_code == 200:
                result = response.json()
                print(f"[RemoteImageUpload] 上传成功: {result.get('message', '')}")
                if 'filename' in result:
                    print(f"[RemoteImageUpload] 保存的文件名: {result['filename']}")
            elif response.status_code == 401:
                print(f"[RemoteImageUpload] 错误: API秘钥验证失败 (401)")
            elif response.status_code == 400:
                error_msg = response.json().get('error', '未知错误')
                print(f"[RemoteImageUpload] 错误: 请求无效 (400) - {error_msg}")
            else:
                print(f"[RemoteImageUpload] 错误: 上传失败，状态码 {response.status_code}")
                try:
                    error_msg = response.json().get('error', response.text)
                    print(f"[RemoteImageUpload] 错误详情: {error_msg}")
                except:
                    print(f"[RemoteImageUpload] 响应内容: {response.text}")
                    
        except requests.exceptions.ConnectionError:
            print(f"[RemoteImageUpload] 错误: 无法连接到服务器 {server_url}")
            print(f"[RemoteImageUpload] 请检查服务器地址是否正确，以及服务器是否正在运行")
        except requests.exceptions.Timeout:
            print(f"[RemoteImageUpload] 错误: 请求超时")
        except requests.exceptions.RequestException as e:
            print(f"[RemoteImageUpload] 错误: 网络请求异常 - {str(e)}")
        except Exception as e:
            print(f"[RemoteImageUpload] 错误: 上传过程中发生异常 - {str(e)}")
            import traceback
            traceback.print_exc()
        
        return ()


# 节点映射（ComfyUI需要这个来注册节点）
NODE_CLASS_MAPPINGS = {
    "zcong Remote Image Upload": RemoteImageUpload,
    "zcong Remote Video Upload": ComfyUIRemoteVideoUpload
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "zcong Remote Image Upload": "zcong Remote Image Upload",
    "zcong Remote Video Upload": "zcong Remote Video Upload"
}
