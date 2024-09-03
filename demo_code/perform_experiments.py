import shutil
import os.path as osp
import subprocess
from subprocess import TimeoutExpired
import sys
import json
from openai import OpenAI
from prompt import *

MAX_ITERS = 4
MAX_RUNS = 5
MAX_STDERR_OUTPUT = 1500


def run_experiment(folder_name, run_num, timeout=7200):
    cwd = osp.abspath(folder_name)  # 获取实验文件夹的绝对路径

    # 复制实验代码文件，以便记录每次运行的代码状态
    shutil.copy(
        osp.join(folder_name, "experiment.py"),
        osp.join(folder_name, f"run_{run_num}.py"),
    )

    # 构建要执行的命令
    command = [
        "python",
        "experiment.py",
        f"--out_dir=run_{run_num}",  # 指定输出目录
    ]

    try:
        # 使用subprocess运行命令
        result = subprocess.run(
            command,  # 要执行的命令
            cwd=cwd,  # 设置当前工作目录
            stderr=subprocess.PIPE,  # 捕获标准错误输出
            text=True,  # 输出以文本形式返回
            timeout=timeout  # 设置超时时间
        )

        # 检查是否有标准错误输出
        if result.stderr:
            print(result.stderr, file=sys.stderr)

        # 检查返回码是否不为0（表示运行失败）
        if result.returncode != 0:
            print(f"Run {run_num} failed with return code {result.returncode}")
            
            # 如果运行失败，删除生成的输出目录
            if osp.exists(osp.join(cwd, f"run_{run_num}")):
                shutil.rmtree(osp.join(cwd, f"run_{run_num}"))
            
            print(f"Run failed with the following error {result.stderr}")
            stderr_output = result.stderr
            
            # 如果标准错误输出超过指定长度，截取部分内容
            if len(stderr_output) > MAX_STDERR_OUTPUT:
                stderr_output = "..." + stderr_output[-MAX_STDERR_OUTPUT:]
            
            # 设置下一步提示信息，包含错误信息
            next_prompt = f"Run failed with the following error {stderr_output}"
        
        else:
            # 运行成功，读取结果文件
            with open(osp.join(cwd, f"run_{run_num}", "final_info.json"), "r") as f:
                results = json.load(f)
            
            # 提取结果中的均值
            results = {k: v["means"] for k, v in results.items()}

            # 设置下一步提示信息，包含运行结果
            next_prompt = f"""Run {run_num} completed. Here are the results:
{results}

Decide if you need to re-plan your experiments given the result (you often will not need to).

Someone else will be using `notes.txt` to perform a writeup on this in the future.
Please include *all* relevant information for the writeup on Run {run_num}, including an experiment description and the run number. Be as verbose as necessary.

Then, implement the next thing on your list.
We will then run the command `python experiment.py --out_dir=run_{run_num + 1}'.
YOUR PROPOSED CHANGE MUST USE THIS COMMAND FORMAT, DO NOT ADD ADDITIONAL COMMAND LINE ARGS.
If you are finished with experiments, respond with 'ALL_COMPLETED'."""
        
        return result.returncode, next_prompt

    except TimeoutExpired:
        # 处理超时情况
        print(f"Run {run_num} timed out after {timeout} seconds")
        
        # 如果运行超时，删除生成的输出目录
        if osp.exists(osp.join(cwd, f"run_{run_num}")):
            shutil.rmtree(osp.join(cwd, f"run_{run_num}"))
        
        next_prompt = f"Run timed out after {timeout} seconds"
        return 1, next_prompt
    

# 运行绘图任务的函数
def run_plotting(folder_name, timeout=600):
    cwd = osp.abspath(folder_name)  # 获取指定文件夹的绝对路径

    # 构建要执行的命令
    command = [
        "python",  # 调用 Python 解释器
        "plot.py",  # 要运行的绘图脚本
    ]

    try:
        # 使用 subprocess 运行命令
        result = subprocess.run(
            command,  # 要执行的命令
            cwd=cwd,  # 设置当前工作目录
            stderr=subprocess.PIPE,  # 捕获标准错误输出
            text=True,  # 以文本模式处理输出
            timeout=timeout  # 设置超时时间（秒）
        )

        # 检查是否有标准错误输出
        if result.stderr:
            print(result.stderr, file=sys.stderr)  # 打印错误信息到标准错误输出

        # 检查返回码是否不为0（表示运行失败）
        if result.returncode != 0:
            print(f"Plotting failed with return code {result.returncode}")
            next_prompt = f"Plotting failed with the following error {result.stderr}"
        else:
            next_prompt = ""  # 如果成功运行，则下一步提示为空
        return result.returncode, next_prompt

    except TimeoutExpired:
        # 处理超时情况
        print(f"Plotting timed out after {timeout} seconds")
        next_prompt = f"Plotting timed out after {timeout} seconds"
        return 1, next_prompt

# 运行多个实验并生成相关图表和笔记的函数
def perform_experiments(idea, folder_name, coder, baseline_results) -> bool:
    ## 运行实验部分
    current_iter = 0  # 初始化当前迭代计数
    run = 1  # 初始化实验运行编号
    next_prompt = coder_prompt.format(
        title=idea["Title"],  # 实验标题
        idea=idea["Experiment"],  # 实验具体方案
        max_runs=MAX_RUNS,  # 最大运行次数
        baseline_results=baseline_results,  # 基准结果
    )
    
    # 循环执行实验，直到达到最大运行次数或成功完成
    while run < MAX_RUNS + 1:
        if current_iter >= MAX_ITERS:  # 检查是否达到最大迭代次数
            print("Max iterations reached")
            break
        coder_out = coder.run(next_prompt)  # 运行 coder，生成实验方案或代码
        print(coder_out)
        
        # 检查 coder 输出是否指示所有实验已完成
        if "ALL_COMPLETED" in coder_out:
            break
        
        # 执行一次实验
        return_code, next_prompt = run_experiment(folder_name, run)
        
        if return_code == 0:  # 实验成功
            run += 1  # 增加运行编号
            current_iter = 0  # 重置迭代计数
        current_iter += 1  # 增加当前迭代计数
    
    # 检查是否因达到最大迭代次数而退出
    if current_iter >= MAX_ITERS:
        print("Not all experiments completed.")
        return False

    ## 绘图部分
    current_iter = 0  # 重置当前迭代计数
    next_prompt = """
Great job! Please modify `plot.py` to generate the most relevant plots for the final writeup. 

In particular, be sure to fill in the "labels" dictionary with the correct names for each run that you want to plot.

Only the runs in the `labels` dictionary will be plotted, so make sure to include all relevant runs.

We will be running the command `python plot.py` to generate the plots.
"""
    
    # 循环执行绘图，直到绘图成功或达到最大迭代次数
    while True:
        coder_out = coder.run(next_prompt)  # 运行 coder 以生成或修改绘图代码
        return_code, next_prompt = run_plotting(folder_name)  # 运行绘图脚本
        current_iter += 1  # 增加当前迭代计数
        if return_code == 0 or current_iter >= MAX_ITERS:
            break

    ## 修改笔记部分
    next_prompt = """
Please modify `notes.txt` with a description of what each plot shows along with the filename of the figure. Please do so in-depth.

Somebody else will be using `notes.txt` to write a report on this in the future.
"""
    
    coder.run(next_prompt)  # 运行 coder 修改 `notes.txt` 以便将来撰写报告

    return True  # 所有实验和绘图步骤均成功完成
