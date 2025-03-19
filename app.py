import asyncio  # 导入异步IO库，用于处理异步操作
import base64  # 导入base64编码/解码库，用于音频数据的编码
import json  # 导入JSON处理库，用于处理JSON格式数据
from pathlib import Path  # 导入Path类，用于处理文件路径

import gradio as gr  # 导入Gradio库，用于创建Web界面
import numpy as np  # 导入NumPy库，用于处理数值数组
import openai  # 导入OpenAI库，用于与OpenAI API交互
from dotenv import load_dotenv  # 导入dotenv库，用于加载环境变量
from fastapi import FastAPI  # 导入FastAPI框架，用于创建Web应用
from fastapi.responses import HTMLResponse, StreamingResponse  # 导入FastAPI响应类型
from fastrtc import (  # 导入fastrtc库，用于实时通信
    AdditionalOutputs,
    AsyncStreamHandler,
    Stream,
    get_twilio_turn_credentials,
    wait_for_item,
)
from gradio.utils import get_space  # 导入Gradio工具函数，用于检测是否在Hugging Face Space环境中
from openai.types.beta.realtime import ResponseAudioTranscriptDoneEvent  # 导入OpenAI实时API事件类型

import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 加载.env文件中的环境变量
load_dotenv()

# 获取当前文件所在目录
cur_dir = Path(__file__).parent

# 设置音频采样率为24kHz
SAMPLE_RATE = 24000


# 定义OpenAI处理器类，继承自AsyncStreamHandler
class OpenAIHandler(AsyncStreamHandler):
    def __init__(
        self,
    ) -> None:
        # 初始化父类，设置音频处理参数
        super().__init__(
            expected_layout="mono",  # 期望的音频布局为单声道
            output_sample_rate=SAMPLE_RATE,  # 输出采样率
            output_frame_size=480,  # 输出帧大小
            input_sample_rate=SAMPLE_RATE,  # 输入采样率
        )
        self.connection = None  # 初始化连接为空
        self.output_queue = asyncio.Queue()  # 创建异步队列，用于存储输出数据

    def copy(self):
        # 创建处理器的副本，用于处理多个连接
        return OpenAIHandler()

    async def start_up(
        self,
    ):
        """连接到OpenAI实时API。在单独的线程中永久运行以保持连接开放。"""
        # 创建OpenAI异步客户端
        self.client = openai.AsyncOpenAI()
        # 连接到OpenAI实时API
        async with self.client.beta.realtime.connect(model="gpt-4o-mini-realtime-preview-2024-12-17") as conn:
            # 更新会话设置，启用服务器端语音活动检测
            await conn.session.update(
                session={"turn_detection": {"type": "server_vad"}}
            )
            self.connection = conn  # 保存连接对象
            # 异步迭代处理来自连接的事件
            async for event in self.connection:
                if event.type == "response.audio_transcript.done":
                    # 如果是音频转录完成事件，将其添加到输出队列
                    await self.output_queue.put(AdditionalOutputs(event))
                if event.type == "response.audio.delta":
                    # 如果是音频增量事件，解码音频数据并添加到输出队列
                    await self.output_queue.put(
                        (
                            self.output_sample_rate,
                            np.frombuffer(
                                base64.b64decode(event.delta), dtype=np.int16
                            ).reshape(1, -1),
                        ),
                    )

    async def receive(self, frame: tuple[int, np.ndarray]) -> None:
        """接收音频帧并发送到OpenAI实时API"""
        if not self.connection:
            return
        _, array = frame  # 解包音频帧，获取音频数组
        array = array.squeeze()  # 移除单维度，转换为一维数组
        audio_message = base64.b64encode(array.tobytes()).decode("utf-8")  # 将音频数据编码为base64字符串
        await self.connection.input_audio_buffer.append(audio=audio_message)  # 将音频数据添加到输入缓冲区

    async def emit(self) -> tuple[int, np.ndarray] | AdditionalOutputs | None:
        """从输出队列中获取并返回下一个项目"""
        return await wait_for_item(self.output_queue)

    async def shutdown(self) -> None:
        """关闭与OpenAI实时API的连接"""
        if self.connection:
            await self.connection.close()
            self.connection = None


def update_chatbot(chatbot: list[dict], response: ResponseAudioTranscriptDoneEvent):
    """更新聊天机器人的消息历史"""
    # 将助手的回复添加到聊天历史中
    chatbot.append({"role": "assistant", "content": response.transcript})
    return chatbot


# 创建Gradio聊天界面组件
chatbot = gr.Chatbot(type="messages")
# 创建不可见的文本框组件，用于存储最新消息
latest_message = gr.Textbox(type="text", visible=False)
# 创建Stream对象，用于处理实时音频通信
stream = Stream(
    OpenAIHandler(),  # 使用OpenAIHandler处理音频
    mode="send-receive",  # 设置模式为发送和接收
    modality="audio",  # 设置模态为音频
    additional_inputs=[chatbot],  # 设置额外输入为聊天机器人组件
    additional_outputs=[chatbot],  # 设置额外输出为聊天机器人组件
    additional_outputs_handler=update_chatbot,  # 设置额外输出处理函数
    rtc_configuration=get_twilio_turn_credentials() if get_space() else None,  # 如果在Hugging Face Space中，使用Twilio TURN凭证
    concurrency_limit=5 if get_space() else None,  # 如果在Hugging Face Space中，限制并发连接数为5
    time_limit=90 if get_space() else None,  # 如果在Hugging Face Space中，限制每个连接的时间为90秒
)

# 创建FastAPI应用
app = FastAPI()

# 将Stream挂载到FastAPI应用
stream.mount(app)


@app.get("/")
async def _():
    """处理根路径请求，返回HTML页面"""
    # 如果在Hugging Face Space中，获取Twilio TURN凭证
    rtc_config = get_twilio_turn_credentials() if get_space() else None
    # 读取HTML模板
    html_content = (cur_dir / "index.html").read_text()
    # 替换模板中的RTC配置
    html_content = html_content.replace("__RTC_CONFIGURATION__", json.dumps(rtc_config))
    # 返回HTML响应
    return HTMLResponse(content=html_content)


@app.get("/outputs")
def _(webrtc_id: str):
    """处理输出流请求，返回服务器发送事件流"""
    async def output_stream():
        """生成输出流"""
        import json

        # 异步迭代处理指定WebRTC ID的输出流
        async for output in stream.output_stream(webrtc_id):
            # 将输出转换为JSON字符串
            s = json.dumps({"role": "assistant", "content": output.args[0].transcript})
            # 生成服务器发送事件格式的数据
            yield f"event: output\ndata: {s}\n\n"

    # 返回流式响应
    return StreamingResponse(output_stream(), media_type="text/event-stream")


if __name__ == "__main__":
    """主程序入口点"""
    import os

    os.environ["no_proxy"] = "localhost,127.0.0.1"

    # 根据环境变量MODE决定运行模式
    if (mode := os.getenv("MODE")) == "UI":
        # UI模式：启动Gradio界面
        stream.ui.launch(server_port=7860)
    elif mode == "PHONE":
        # PHONE模式：启动FastPhone服务
        stream.fastphone(host="0.0.0.0", port=7860)
    else:
        # 默认模式：启动FastAPI服务
        import uvicorn

        uvicorn.run(app, host="0.0.0.0", port=7860)
