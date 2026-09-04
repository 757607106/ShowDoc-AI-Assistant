我需基于当前项目做迭代，要爬取showDoc平台的接口文档的项目内容，最后下载导出md格式文件，新增了1和2个接口，3为现有需求的接口，逻辑正确


1、先登录，获取token
    1、1登录前需要获取验证码，需要传参captcha_id和captcha，captcha_id为验证码id，captcha为验证码的值，需要先获取验证码id，然后获取验证码值，然后传参captcha_id和captcha，然后登录接口返回token
        验证码接口：https://yunhelp.gmgrasp.com.cn/server/index.php?s=/api/common/createCaptcha
        请求方式：POST
        请求参数：s：/api/common/createCaptcha
        获取接口返回：captcha_id，captcha 使用jsonpath获取结果，提取表达式：$.data.captcha_id
    1、2 验证码图片地址：https://yunhelp.gmgrasp.com.cn/server/index.php?s=…/common/showCaptcha&captcha_id=7668&1766563147000 其中captcha_id为验证码id和当前时间戳。
    图片识别选用 PaddleOCR AIP，访问令牌请通过环境变量配置，勿写入仓库。
    调用代码示例：
# Please make sure the requests library is installed
# pip install requests
import base64
import os
import requests

API_URL = "https://tesd2d4305w2s341.aistudio-app.com/layout-parsing"
TOKEN = os.getenv("PADDLEOCR_API_TOKEN")

file_path = "<local file path>"

with open(file_path, "rb") as file:
    file_bytes = file.read()
    file_data = base64.b64encode(file_bytes).decode("ascii")

headers = {
    "Authorization": f"token {TOKEN}",
    "Content-Type": "application/json"
}

required_payload = {
    "file": file_data,
    "fileType": <file type>,  # For PDF documents, set `fileType` to 0; for images, set `fileType` to 1
}

optional_payload = {
    "useDocOrientationClassify": False,
    "useDocUnwarping": False,
    "useChartRecognition": False,
}

payload = {**required_payload, **optional_payload}

response = requests.post(API_URL, json=payload, headers=headers)
print(response.status_code)
assert response.status_code == 200
result = response.json()["result"]

output_dir = "output"
os.makedirs(output_dir, exist_ok=True)

for i, res in enumerate(result["layoutParsingResults"]):
    md_filename = os.path.join(output_dir, f"doc_{i}.md")
    with open(md_filename, "w", encoding="utf-8") as md_file:
        md_file.write(res["markdown"]["text"])
    print(f"Markdown document saved at {md_filename}")
    for img_path, img in res["markdown"]["images"].items():
        full_img_path = os.path.join(output_dir, img_path)
        os.makedirs(os.path.dirname(full_img_path), exist_ok=True)
        img_bytes = requests.get(img).content
        with open(full_img_path, "wb") as img_file:
            img_file.write(img_bytes)
        print(f"Image saved to: {full_img_path}")
    for img_name, img in res["outputImages"].items():
        img_response = requests.get(img)
        if img_response.status_code == 200:
            # Save image to local
            filename = os.path.join(output_dir, f"{img_name}_{i}.jpg")
            with open(filename, "wb") as f:
                f.write(img_response.content)
            print(f"Image saved to: {filename}")
        else:
            print(f"Failed to download image, status code: {img_response.status_code}")
    1、3 请求1、2 接口需要识别图片中的数字并返回验证码数字
    1、4 登录接口：https://yunhelp.gmgrasp.com.cn/server/index.php?s=/api/user/loginByVerify
        请求方式：POST
        请求参数：请求参数：s：/api/user/loginByVerify 表单数据：username=<username>&password=<password>&captcha=6183&captcha_id=7664&redirect_login=false
        获取接口返回：token使用jsonpath获取结果，提取表达式：$.data.user_token  

2、获取项目列表
    请求接口：https://yunhelp.gmgrasp.com.cn/server/index.php?s=/api/item/myList
    请求方式：POST
    请求参数：s：/api/item/myList 表单数据：item_group_id=0&user_token=<user_token>  其中user_token为登录接口返回的token
    获取接口返回：item_id，item_name 使用jsonpath获取结果，提取表达式：$.data[*].item_id，$.data[*].item_name 其中item_id和item_name为项目id和项目名称item_id为项目id，item_name为项目名称
    
3、https://yunhelp.gmgrasp.com.cn/server/index.php?s=/api/item/info 接口和 https://yunhelp.gmgrasp.com.cn/server/index.php?s=/api/page/info 接口和当前项目的结构逻辑一样，无需要处理，只是传人的参数不一样
 

前端页面需求：
1️需要支持选择项目，选择项目后，需要获取选择项目并下载
2️页面排版样式美观，交互友好，需要考虑用户体验友好
3️需要支持导出为md格式，需要考虑用户体验友好
4️需要支持搜索功能，需要考虑用户体验友好
5️需要支持导出为html格式，需要考虑用户体验友好
6️需要支持选择项目后，支持预览内容，需要考虑用户体验友好，需要考虑用户体验友好






