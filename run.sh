#!/bin/bash

function find_python_command() {
    if command -v python &> /dev/null
    then
        echo "python"
    elif command -v python3 &> /dev/null
    then
        echo "python3"
    else
        echo "Python没有找到，请安装Python."
        exit 1
    fi
}

PYTHON_CMD=$(find_python_command)

$PYTHON_CMD scripts/check_requirements.py requirements.txt
if [ $? -eq 1 ]
then
    echo Installing missing packages...
    $PYTHON_CMD -m pip install -r requirements.txt
fi
$PYTHON_CMD -m autogpt $@
read -p "按任意键继续..."