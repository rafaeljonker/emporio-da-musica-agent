from pathlib import Path

from emporio.local_model import LocalPlan, choose_local_model, setup_commands


def test_mac_32gb_gets_31b_native():
    plan = choose_local_model("Darwin", "arm64", nvidia=False, mem_gib=32)
    assert (plan.route, plan.tag, plan.download_gb) == ("native", "gemma4:31b", 20)


def test_mac_16gb_gets_12b():
    plan = choose_local_model("Darwin", "arm64", nvidia=False, mem_gib=16)
    assert (plan.route, plan.tag, plan.min_ram_gb) == ("native", "gemma4:12b", 16)


def test_linux_nvidia_gets_docker_gpu_31b():
    plan = choose_local_model("Linux", "x86_64", nvidia=True, mem_gib=16)
    assert (plan.route, plan.tag) == ("docker-nvidia", "gemma4:31b")


def test_small_cpu_box_gets_e4b():
    plan = choose_local_model("Linux", "x86_64", nvidia=False, mem_gib=8)
    assert (plan.route, plan.tag) == ("docker-cpu", "gemma4:e4b")
    assert plan.seconds_per_reply


def test_docker_route_runs_ollama_inside_compose():
    plan = LocalPlan("docker-cpu", "gemma4:e4b", 10, 8, "estimate")
    steps = setup_commands(plan, "emporio-gemma", Path("Modelfile"))
    assert steps[0][-4:] == ["up", "-d", "--wait", "ollama"]
    assert steps[1][-6:] == ["exec", "-T", "ollama", "ollama", "pull", "gemma4:e4b"]
    assert steps[-1][-4:] == ["create", "emporio-gemma", "-f", "/root/Modelfile"]


def test_nvidia_route_uses_the_gpu_compose_service():
    plan = LocalPlan("docker-nvidia", "gemma4:31b", 20, 32, "estimate")
    steps = setup_commands(plan, "emporio-gemma", Path("Modelfile"))
    assert steps[0][-4:] == ["up", "-d", "--wait", "ollama-nvidia"]
    assert all("ollama-nvidia" in step for step in steps[1:2] + steps[3:])
    assert steps[2][-1] == "ollama-nvidia:/root/Modelfile"
