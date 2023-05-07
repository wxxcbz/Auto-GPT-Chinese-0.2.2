"""Handles loading of plugins."""

import importlib
import json
import os
import zipfile
from pathlib import Path
from typing import List, Optional, Tuple
from urllib.parse import urlparse
from zipimport import zipimporter

import openapi_python_client
import requests
from auto_gpt_plugin_template import AutoGPTPluginTemplate
from openapi_python_client.cli import Config as OpenAPIConfig

from autogpt.config import Config
from autogpt.logs import logger
from autogpt.models.base_open_ai_plugin import BaseOpenAIPlugin


def inspect_zip_for_modules(zip_path: str, debug: bool = False) -> list[str]:
    """
    Inspect a zipfile for a modules.

    Args:
        zip_path (str): Path to the zipfile.
        debug (bool, optional): Enable debug logging. Defaults to False.

    Returns:
        list[str]: The list of module names found or empty list if none were found.
    """
    result = []
    with zipfile.ZipFile(zip_path, "r") as zfile:
        for name in zfile.namelist():
            if name.endswith("__init__.py") and not name.startswith("__MACOSX"):
                logger.debug(f"发现模块 '{name}' 的zip文件: {name}")
                result.append(name)
    if len(result) == 0:
        logger.debug(f"模块 '__init__.py' 没有在zip文件中找到 @ {zip_path}.")
    return result


def write_dict_to_json_file(data: dict, file_path: str) -> None:
    """
    Write a dictionary to a JSON file.
    Args:
        data (dict): Dictionary to write.
        file_path (str): Path to the file.
    """
    with open(file_path, "w") as file:
        json.dump(data, file, indent=4)


def fetch_openai_plugins_manifest_and_spec(cfg: Config) -> dict:
    """
    Fetch the manifest for a list of OpenAI plugins.
        Args:
        urls (List): List of URLs to fetch.
    Returns:
        dict: per url dictionary of manifest and spec.
    """
    # TODO add directory scan
    manifests = {}
    for url in cfg.plugins_openai:
        openai_plugin_client_dir = f"{cfg.plugins_dir}/openai/{urlparse(url).netloc}"
        create_directory_if_not_exists(openai_plugin_client_dir)
        if not os.path.exists(f"{openai_plugin_client_dir}/ai-plugin.json"):
            try:
                response = requests.get(f"{url}/.well-known/ai-plugin.json")
                if response.status_code == 200:
                    manifest = response.json()
                    if manifest["schema_version"] != "v1":
                        logger.warn(
                            f"不支持的版本: {manifest['schem_version']} for {url}"
                        )
                        continue
                    if manifest["api"]["type"] != "openapi":
                        logger.warn(
                            f"不支持的API: {manifest['api']['type']} for {url}"
                        )
                        continue
                    write_dict_to_json_file(
                        manifest, f"{openai_plugin_client_dir}/ai-plugin.json"
                    )
                else:
                    logger.warn(
                        f"获取清单失败 {url}: {response.status_code}"
                    )
            except requests.exceptions.RequestException as e:
                logger.warn(f"获取清单错误 {url}: {e}")
        else:
            logger.info(f"清单 {url} 已经存在")
            manifest = json.load(open(f"{openai_plugin_client_dir}/ai-plugin.json"))
        if not os.path.exists(f"{openai_plugin_client_dir}/openapi.json"):
            openapi_spec = openapi_python_client._get_document(
                url=manifest["api"]["url"], path=None, timeout=5
            )
            write_dict_to_json_file(
                openapi_spec, f"{openai_plugin_client_dir}/openapi.json"
            )
        else:
            logger.info(f"OpenAPI 配置 {url} 已经存在")
            openapi_spec = json.load(open(f"{openai_plugin_client_dir}/openapi.json"))
        manifests[url] = {"manifest": manifest, "openapi_spec": openapi_spec}
    return manifests


def create_directory_if_not_exists(directory_path: str) -> bool:
    """
    Create a directory if it does not exist.
    Args:
        directory_path (str): Path to the directory.
    Returns:
        bool: True if the directory was created, else False.
    """
    if not os.path.exists(directory_path):
        try:
            os.makedirs(directory_path)
            logger.debug(f"生成目录: {directory_path}")
            return True
        except OSError as e:
            logger.warn(f"生成目录错误 {directory_path}: {e}")
            return False
    else:
        logger.info(f"目录 {directory_path} 已经存在")
        return True


def initialize_openai_plugins(
    manifests_specs: dict, cfg: Config, debug: bool = False
) -> dict:
    """
    Initialize OpenAI plugins.
    Args:
        manifests_specs (dict): per url dictionary of manifest and spec.
        cfg (Config): Config instance including plugins config
        debug (bool, optional): Enable debug logging. Defaults to False.
    Returns:
        dict: per url dictionary of manifest, spec and client.
    """
    openai_plugins_dir = f"{cfg.plugins_dir}/openai"
    if create_directory_if_not_exists(openai_plugins_dir):
        for url, manifest_spec in manifests_specs.items():
            openai_plugin_client_dir = f"{openai_plugins_dir}/{urlparse(url).hostname}"
            _meta_option = (openapi_python_client.MetaType.SETUP,)
            _config = OpenAPIConfig(
                **{
                    "project_name_override": "client",
                    "package_name_override": "client",
                }
            )
            prev_cwd = Path.cwd()
            os.chdir(openai_plugin_client_dir)
            Path("ai-plugin.json")
            if not os.path.exists("client"):
                client_results = openapi_python_client.create_new_client(
                    url=manifest_spec["manifest"]["api"]["url"],
                    path=None,
                    meta=_meta_option,
                    config=_config,
                )
                if client_results:
                    logger.warn(
                        f"建立OpenAPI客户端错误: {client_results[0].header} \n"
                        f" details: {client_results[0].detail}"
                    )
                    continue
            spec = importlib.util.spec_from_file_location(
                "client", "client/client/client.py"
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            client = module.Client(base_url=url)
            os.chdir(prev_cwd)
            manifest_spec["client"] = client
    return manifests_specs


def instantiate_openai_plugin_clients(
    manifests_specs_clients: dict, cfg: Config, debug: bool = False
) -> dict:
    """
    Instantiates BaseOpenAIPlugin instances for each OpenAI plugin.
    Args:
        manifests_specs_clients (dict): per url dictionary of manifest, spec and client.
        cfg (Config): Config instance including plugins config
        debug (bool, optional): Enable debug logging. Defaults to False.
    Returns:
          plugins (dict): per url dictionary of BaseOpenAIPlugin instances.

    """
    plugins = {}
    for url, manifest_spec_client in manifests_specs_clients.items():
        plugins[url] = BaseOpenAIPlugin(manifest_spec_client)
    return plugins


def scan_plugins(cfg: Config, debug: bool = False) -> List[AutoGPTPluginTemplate]:
    """Scan the plugins directory for plugins and loads them.

    Args:
        cfg (Config): Config instance including plugins config
        debug (bool, optional): Enable debug logging. Defaults to False.

    Returns:
        List[Tuple[str, Path]]: List of plugins.
    """
    loaded_plugins = []
    # Generic plugins
    plugins_path_path = Path(cfg.plugins_dir)

    logger.debug(f"Plugins允许清单: {cfg.plugins_allowlist}")
    logger.debug(f"Plugins禁止清单: {cfg.plugins_denylist}")

    for plugin in plugins_path_path.glob("*.zip"):
        if moduleList := inspect_zip_for_modules(str(plugin), debug):
            for module in moduleList:
                plugin = Path(plugin)
                module = Path(module)
                logger.debug(f"Plugin: {plugin} Module: {module}")
                zipped_package = zipimporter(str(plugin))
                zipped_module = zipped_package.load_module(str(module.parent))
                for key in dir(zipped_module):
                    if key.startswith("__"):
                        continue
                    a_module = getattr(zipped_module, key)
                    a_keys = dir(a_module)
                    if (
                        "_abc_impl" in a_keys
                        and a_module.__name__ != "AutoGPTPluginTemplate"
                        and denylist_allowlist_check(a_module.__name__, cfg)
                    ):
                        loaded_plugins.append(a_module())
    # OpenAI plugins
    if cfg.plugins_openai:
        manifests_specs = fetch_openai_plugins_manifest_and_spec(cfg)
        if manifests_specs.keys():
            manifests_specs_clients = initialize_openai_plugins(
                manifests_specs, cfg, debug
            )
            for url, openai_plugin_meta in manifests_specs_clients.items():
                if denylist_allowlist_check(url, cfg):
                    plugin = BaseOpenAIPlugin(openai_plugin_meta)
                    loaded_plugins.append(plugin)

    if loaded_plugins:
        logger.info(f"\nPlugins 找到: {len(loaded_plugins)}\n" "--------------------")
    for plugin in loaded_plugins:
        logger.info(f"{plugin._name}: {plugin._version} - {plugin._description}")
    return loaded_plugins


def denylist_allowlist_check(plugin_name: str, cfg: Config) -> bool:
    """Check if the plugin is in the allowlist or denylist.

    Args:
        plugin_name (str): Name of the plugin.
        cfg (Config): Config object.

    Returns:
        True or False
    """
    logger.debug(f"检查plugin {plugin_name} 是否可以加载")
    if plugin_name in cfg.plugins_denylist:
        logger.debug(f"没有加载plugin {plugin_name} 在禁止清单上.")
        return False
    if plugin_name in cfg.plugins_allowlist:
        logger.debug(f"成功加载plugin {plugin_name} 在允许清单上.")
        return True
    ack = input(
        f"警告: Plugin {plugin_name} 已找到. 但是不在"
        f" 允许清单中... 加载? ({cfg.authorise_key}/{cfg.exit_key}): "
    )
    return ack.lower() == cfg.authorise_key
