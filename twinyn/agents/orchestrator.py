from collections import deque
from .seed_agent import SeedTask, SeedOutput

class Orchestrator:
    """
    Orchestrator class to orchestrate the execution of tasks.

    Attributes:
        seedprompts (list[str]): A list of seed prompts.
        seed_task_kwargs (dict): Keyword arguments for the seed task.
        tasks_by_layer (list[list[Task]]): A list of lists of tasks, where each inner list represents a layer of tasks.
        max_depth (int): The maximum depth of the task tree.
        branching_factor (int): The branching factor of the task tree at each analysis node.
    """

    def __init__(self, seedprompts: list[str], max_depth: int=2, branching_factor: int=2, **seed_task_kwargs):
        self.seedprompts = seedprompts
        self.seed_task_kwargs = seed_task_kwargs
        self.tasks_by_layer = []
        self.max_depth = max_depth
        self.branching_factor = branching_factor
    
    def run(self):
        """Runs the task tree."""
        curr_layer_prompts = deque(self.seedprompts)
        for _ in range(self.max_depth):
            if not curr_layer_prompts:
                break

            curr_layer_tasks = self._process_layer(curr_layer_prompts)
            self.tasks_by_layer.append(curr_layer_tasks)

            next_layer_prompts = self._get_further_prompts(curr_layer_tasks)
            curr_layer_prompts = deque(next_layer_prompts)

            # break out since no further prompts are generated
            if self.branching_factor == 0:
                break

    def _process_layer(self, curr_layer_prompts):
        """Processes a layer of tasks and returns a list of task objects."""
        tasks = []
        while curr_layer_prompts:
            prompt = curr_layer_prompts.popleft()
            # prompt might be []
            if not prompt:
                continue
            task = SeedTask(**self.seed_task_kwargs, seed_prompt=prompt, branching_factor=self.branching_factor)
            task.kickoff()
            tasks.append(task)
        return tasks

    def _get_further_prompts(self, tasks):
        """Given the task objects, returns a list of "further" prompts."""
        outputs = [SeedOutput(task.chat_result) for task in tasks]
        further_prompts = []
        for output in outputs:
            output.collect()
            further_prompts.extend(output.parsed_instructions)
        return further_prompts