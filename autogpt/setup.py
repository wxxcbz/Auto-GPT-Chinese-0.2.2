"""Set up the AI and its goals"""
import re

from colorama import Fore, Style

from autogpt import utils
from autogpt.config import Config
from autogpt.config.ai_config import AIConfig
from autogpt.llm import create_chat_completion
from autogpt.logs import logger

CFG = Config()


def prompt_user() -> AIConfig:
    """Prompt the user for input

    Returns:
        AIConfig: The AIConfig object tailored to the user's input
    """
    ai_name = ""
    ai_config = None

    # Construct the prompt
    logger.typewriter_log(
        "欢迎使用RealHossie的汉化版Auto-GPT!",
        Fore.GREEN,
    )
    logger.typewriter_log(
        "也欢迎关注我的频道www.youtube.com/@hossie",
        Fore.LIGHTBLUE_EX,
        "执行 '--help' 获取更多信息.",
        speak_text=True,
    )

    # Get user desire
    logger.typewriter_log(
        "创建一个AI助手:",
        Fore.GREEN,
        "输入 '--manual' 进入手动模式.",
        speak_text=True,
    )

    user_desire = utils.clean_input(
        f"{Fore.LIGHTBLUE_EX}我希望Auto-GPT帮我{Style.RESET_ALL}: "
    )

    if user_desire == "":
        user_desire = "写一篇wikipedia风格的文章，关于此项目: https://github.com/RealHossie/Auto-GPT-Chinese"  # Default prompt

    # If user desire contains "--manual"
    if "--manual" in user_desire:
        logger.typewriter_log(
            "手动模式已启动",
            Fore.GREEN,
            speak_text=True,
        )
        return generate_aiconfig_manual()

    else:
        try:
            return generate_aiconfig_automatic(user_desire)
        except Exception as e:
            logger.typewriter_log(
                "无法基于用户偏好生成AI配置.",
                Fore.RED,
                "回滚至手动模式.",
                speak_text=True,
            )

            return generate_aiconfig_manual()


def generate_aiconfig_manual() -> AIConfig:
    """
    Interactively create an AI configuration by prompting the user to provide the name, role, and goals of the AI.

    This function guides the user through a series of prompts to collect the necessary information to create
    an AIConfig object. The user will be asked to provide a name and role for the AI, as well as up to five
    goals. If the user does not provide a value for any of the fields, default values will be used.

    Returns:
        AIConfig: An AIConfig object containing the user-defined or default AI name, role, and goals.
    """

    # Manual Setup Intro
    logger.typewriter_log(
        "建立一个AI助手:",
        Fore.GREEN,
        "给你AI助手起一个名字和赋予它一个角色，什么都不输入将使用默认值.",
        speak_text=True,
    )

    # Get AI Name from User
    logger.typewriter_log(
        "你AI的名字叫: ", Fore.GREEN, "例如, '企业家-GPT'"
    )
    ai_name = utils.clean_input("AI 名字: ")
    if ai_name == "":
        ai_name = "企业家-GPT"

    logger.typewriter_log(
        f"{ai_name} 在这儿呢!", Fore.LIGHTBLUE_EX, "我听从您的吩咐.", speak_text=True
    )

    # Get AI Role from User
    logger.typewriter_log(
        "描述你AI的角色: ",
        Fore.GREEN,
        "例如, '一个自动帮助你策划与经营业务的人工智能帮手，目标专注于提升你的净资产.'",
    )
    ai_role = utils.clean_input(f"{ai_name} is: ")
    if ai_role == "":
        ai_role = "一个自动帮助你策划与经营业务的人工智能帮手，目标专注于提升你的净资产."

    # Enter up to 5 goals for the AI
    logger.typewriter_log(
        "为你的AI定义最多5个目标: ",
        Fore.GREEN,
        "例如: \n提升净资产, 增长Twitter账户, 自动化策划与管理多条业务线'",
    )
    logger.info("什么都不输入将加载默认值，输入结束后直接按回车.")
    ai_goals = []
    for i in range(5):
        ai_goal = utils.clean_input(f"{Fore.LIGHTBLUE_EX}目标{Style.RESET_ALL} {i+1}: ")
        if ai_goal == "":
            break
        ai_goals.append(ai_goal)
    if not ai_goals:
        ai_goals = [
            "提升净资产",
            "增长Twitter账户",
            "自动化策划与管理多条业务线",
        ]

    # Get API Budget from User
    logger.typewriter_log(
        "输入你的API预算: ",
        Fore.GREEN,
        "例如: $1.50",
    )
    logger.info("什么都不输入将让你的AI驰骋飞翔")
    api_budget_input = utils.clean_input(
        f"{Fore.LIGHTBLUE_EX}预算{Style.RESET_ALL}: $"
    )
    if api_budget_input == "":
        api_budget = 0.0
    else:
        try:
            api_budget = float(api_budget_input.replace("$", ""))
        except ValueError:
            logger.typewriter_log(
                "错误的预算输入. 开启吃撑飞翔模式.", Fore.RED
            )
            api_budget = 0.0

    return AIConfig(ai_name, ai_role, ai_goals, api_budget)


def generate_aiconfig_automatic(user_prompt) -> AIConfig:
    """Generates an AIConfig object from the given string.

    Returns:
    AIConfig: The AIConfig object tailored to the user's input
    """

    system_prompt = """
你的任务是作为一个自动化的助手，设计5个最高效的目标和一个最合适你角色名字(_GPT), 确保这些目标与所分配的任务达到最佳的一致性并成功完成.

用户会提出任务，你只需按照下面的格式提供输出，无需解释或对话.

输入示例:
在业务营销方面帮助我

输出示例:
名字: CMOGPT
描述: 一名专业的数字营销人工智能助手，为独立创业者提供世界级的专业知识，解决软件即服务（SaaS）、内容产品、代理商等领域的营销问题，助力企业发展.
目标:
- 我作为您的虚拟首席营销官，我将积极参与有效的问题解决、优先事项排序、规划和支持执行，以满足您的营销需求.

- 我将提供具体、可操作且简洁的建议，帮助您在不使用陈词滥调或过多解释的情况下做出明智的决策.

- 我将识别并优先选择快速获胜和高性价比的营销活动，以最少的时间和预算投入实现最大化的结果.

- 我在面对不明确的信息或不确定性时，主动引导您并提供建议，确保您的营销策略保持正确的方向.
"""

    # Call LLM with the string as user input
    messages = [
        {
            "role": "system",
            "content": system_prompt,
        },
        {
            "role": "user",
            "content": f"任务: '{user_prompt}'\n仅以系统提示中指定的格式回应，不需要进行解释或对话.\n",
        },
    ]
    output = create_chat_completion(messages, CFG.fast_llm_model)

    # Debug LLM Output
    logger.debug(f"AI配置生成原始输出: {output}")

    # Parse the output
    ai_name = re.search(r"名字(?:\s*):(?:\s*)(.*)", output, re.IGNORECASE).group(1)
    ai_role = (
        re.search(
            r"描述(?:\s*):(?:\s*)(.*?)(?:(?:\n)|目标)",
            output,
            re.IGNORECASE | re.DOTALL,
        )
        .group(1)
        .strip()
    )
    ai_goals = re.findall(r"(?<=\n)-\s*(.*)", output)
    api_budget = 0.0  # TODO: parse api budget using a regular expression

    return AIConfig(ai_name, ai_role, ai_goals, api_budget)
