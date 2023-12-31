from colorama import Fore

from autogpt.config.ai_config import AIConfig
from autogpt.config.config import Config
from autogpt.llm import ApiManager
from autogpt.logs import logger
from autogpt.prompts.generator import PromptGenerator
from autogpt.setup import prompt_user
from autogpt.utils import clean_input

CFG = Config()

DEFAULT_TRIGGERING_PROMPT = (
    "确定下一步使用的命令，并使用上面规定的格式进行回答:"
)


def build_default_prompt_generator() -> PromptGenerator:
    """
    This function generates a prompt string that includes various constraints,
        commands, resources, and performance evaluations.

    Returns:
        str: The generated prompt string.
    """

    # Initialize the PromptGenerator object
    prompt_generator = PromptGenerator()

    # Add constraints to the PromptGenerator object
    prompt_generator.add_constraint(
        "短期记忆大概2500字，由于字数限制，你需要将重要的信息尽快写入文件."
    )
    prompt_generator.add_constraint(
        "如果你不确定之前做过什么或者无法找到过往的事件，尝试类似事件可以帮助你回忆."
    )
    prompt_generator.add_constraint("无用户干预")
    prompt_generator.add_constraint(
        '严格采用双引号中的命令，例如 "命令名称"'
    )

    # Add resources to the PromptGenerator object
    prompt_generator.add_resource(
        "去互联网访问与收集信息."
    )
    prompt_generator.add_resource("长期记忆管理.")
    prompt_generator.add_resource(
        "使用GPT-3.5处理简单任务."
    )
    prompt_generator.add_resource("文件输出.")

    # Add performance evaluations to the PromptGenerator object
    prompt_generator.add_performance_evaluation(
        "持续回顾与分析你的行为是否为最优解决方案."
    )
    prompt_generator.add_performance_evaluation(
        "持续自我调整，满足全局目标."
    )
    prompt_generator.add_performance_evaluation(
        "基于过去的决策与策略，优化你的方法."
    )
    prompt_generator.add_performance_evaluation(
        "每一次命令都有回花费成本，因此要聪明与高效的在最少步骤内完成任务."
    )
    prompt_generator.add_performance_evaluation("将所有代码写入一个文件.")
    return prompt_generator


def construct_main_ai_config() -> AIConfig:
    """Construct the prompt for the AI to respond to

    Returns:
        str: The prompt string
    """
    config = AIConfig.load(CFG.ai_settings_file)
    if CFG.skip_reprompt and config.ai_name:
        logger.typewriter_log("名称 :", Fore.GREEN, config.ai_name)
        logger.typewriter_log("角色 :", Fore.GREEN, config.ai_role)
        logger.typewriter_log("目标:", Fore.GREEN, f"{config.ai_goals}")
        logger.typewriter_log(
            "API 预算:",
            Fore.GREEN,
            "无限" if config.api_budget <= 0 else f"${config.api_budget}",
        )
    elif config.ai_name:
        logger.typewriter_log(
            "您回来啦! ",
            Fore.GREEN,
            f"您还希望继续使用 {config.ai_name}吗?",
            speak_text=True,
        )
        should_continue = clean_input(
            f"""继续使用上次的配置吗？?
名称:  {config.ai_name}
角色:  {config.ai_role}
目标: {config.ai_goals}
API 预算: {"infinite" if config.api_budget <= 0 else f"${config.api_budget}"}
继续 ({CFG.authorise_key}/{CFG.exit_key}): """
        )
        if should_continue.lower() == CFG.exit_key:
            config = AIConfig()

    if not config.ai_name:
        config = prompt_user()
        config.save(CFG.ai_settings_file)

    # set the total api budget
    api_manager = ApiManager()
    api_manager.set_total_budget(config.api_budget)

    # Agent Created, print message
    logger.typewriter_log(
        config.ai_name,
        Fore.LIGHTBLUE_EX,
        "已经被建立成功，具体信息如下:",
        speak_text=True,
    )

    # Print the ai config details
    # Name
    logger.typewriter_log("名称:", Fore.GREEN, config.ai_name, speak_text=False)
    # Role
    logger.typewriter_log("角色:", Fore.GREEN, config.ai_role, speak_text=False)
    # Goals
    logger.typewriter_log("目标:", Fore.GREEN, "", speak_text=False)
    for goal in config.ai_goals:
        logger.typewriter_log("-", Fore.GREEN, goal, speak_text=False)

    return config
