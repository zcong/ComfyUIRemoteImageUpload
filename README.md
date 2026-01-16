# ComfyUI远程图片上传节点

这是ComfyUI的自定义节点，用于将生成的图片上传到远程服务器。

## 功能特性

- ✅ 支持图片输入（IMAGE类型）
- ✅ 手动输入API秘钥进行身份验证
- ✅ HTTP POST上传，使用X-API-KEY header进行验证
- ✅ 可配置服务器地址
- ✅ 完整的错误处理和日志输出
- ✅ 无输出参数（仅执行上传操作）

## 安装步骤

### 1. 复制节点文件

将 `remote_image_upload` 目录复制到你的ComfyUI安装目录下的 `custom_nodes` 文件夹中：

```bash
# 假设ComfyUI安装在 /path/to/ComfyUI
cp -r remote_image_upload /path/to/ComfyUI/custom_nodes/
```

### 2. 安装依赖

在ComfyUI环境中安装必要的Python包：

```bash
pip install requests pillow
```

注意：ComfyUI通常已经安装了torch和numpy，如果没有，也需要安装：
```bash
pip install torch numpy
```

### 3. 重启ComfyUI

安装节点后，需要重启ComfyUI才能加载新节点。

## 使用方法

### 在ComfyUI中使用节点

1. 在ComfyUI界面中，找到节点菜单
2. 导航到 `image/remote` 分类
3. 添加 `Remote Image Upload` 节点
4. 连接图片输入到节点的 `image` 输入
5. 在 `api_key` 字段中输入你在服务端配置的API密钥
6. 在 `server_url` 字段中输入服务端地址（例如：`http://localhost:65360/upload`）
7. 执行workflow，节点会自动上传图片

### 节点参数说明

- **image** (IMAGE): 要上传的图片，从其他节点连接
- **api_key** (STRING): API密钥，必须与服务端配置的密钥一致
- **server_url** (STRING): 服务端上传地址，格式：`http://服务器地址:端口/upload`

## 服务端要求

本节点需要配合服务端使用。服务端代码请参考：
- [ComfyUIRemoteImageUploadServer](https://github.com/zcong/ComfyUIRemoteImageUploadServer)

## 错误处理

节点会在ComfyUI的控制台输出详细的错误信息，包括：
- 网络连接错误
- API密钥验证失败
- 服务器错误响应
- 其他异常情况

## 故障排查

### 节点无法上传

1. 检查服务端是否正在运行
2. 检查服务器地址和端口是否正确
3. 检查API密钥是否匹配
4. 查看ComfyUI控制台的错误信息

### 节点未显示

1. 确认节点文件已正确复制到 `custom_nodes` 目录
2. 检查Python依赖是否安装完整
3. 重启ComfyUI
4. 查看ComfyUI启动日志，检查是否有错误信息

## 许可证

MIT License

