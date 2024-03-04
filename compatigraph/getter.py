import subprocess
import time

from graphviz import Digraph


def parse_dependencies(dependency_text):
    dependencies = {}
    current_package = None

    for line in dependency_text.strip().split("\n"):
        if line.startswith("  Depends: "):
            _, dep = line.split(":", 1)
            dep_name, _, version = dep.partition(" ")
            version = version.strip("()") if version else None
            if current_package:
                if current_package not in dependencies:
                    dependencies[current_package] = []
                dependencies[current_package].append((dep_name.strip(), version))
        else:
            current_package = line.strip()
            if current_package not in dependencies:
                dependencies[current_package] = []

    return dependencies


def get_dependencies(package_name):
    """
    Get all dependencies for a given package on Debian-based systems.
    """
    try:
        result = subprocess.run(
            ["apt-rdepends", package_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True
        )
        dependencies = result.stdout.decode("utf-8")

        return parse_dependencies(dependencies)
    except subprocess.CalledProcessError as e:
        print(f"Error occurred: {e}")
        return {}


def build_dependency_graph(package_name, graph=None, visited=None):
    """
    Recursively build a graph of dependencies for a given package.
    """
    if graph is None:
        graph = Digraph(comment=f"Dependency Graph for {package_name}", format="png")
    if visited is None:
        visited = set()

    if package_name not in visited:
        visited.add(package_name)
        dependencies = get_dependencies(package_name)
        start_time = time.time()
        for dep in dependencies:
            if dep and dep not in visited:
                graph.edge(package_name, dep)
                build_dependency_graph(dep, graph, visited)
        end_time = time.time()
        duration = end_time - start_time  # Вычисляем длительность выполнения
        print(f"Время выполнения: {duration} секунд")

    return graph


# Replace 'emacs' with the package name you're interested in
package_name = "vim"

dependency_graph = build_dependency_graph(package_name)

# Render the graph to a file
output_filename = "dependency_graph"
dependency_graph.render(output_filename)

print(f"Dependency graph created: {output_filename}.png")
