"""
Autonomous Loop — Plan/Research/Execute/Observe/Reflect/Report
Multi-step autonomous execution with retry and self-correction.
"""
import asyncio
import json
import uuid
from typing import Any, Callable, Coroutine, Dict, List, Optional

class AutonomousLoop:
    """
    Autonomous execution loop for complex multi-step tasks.

    Flow:
    1. PLAN — Break task into steps
    2. RESEARCH — Gather info (web search, file read, etc.)
    3. EXECUTE — Run each step
    4. OBSERVE — Check results
    5. REFLECT — Evaluate success, decide next action
    6. REPORT — Summarize to user
    """

    MAX_ITERATIONS = 10

    def __init__(
        self,
        llm_callback: Callable[[str], Coroutine[Any, Any, str]],
        tool_callback: Callable[[str, Dict], Coroutine[Any, Any, str]],
        on_step: Optional[Callable[[int, str, str], Coroutine[Any, Any, None]]] = None,
    ):
        self.llm = llm_callback
        self.tool = tool_callback
        self.on_step = on_step
        self._cancelled = False

    async def run(self, task: str, context: str = "") -> Dict[str, Any]:
        """
        Run autonomous loop for a task.

        Returns:
            Dict with: task, plan, steps, status, result, iterations
        """
        self._cancelled = False
        task_id = str(uuid.uuid4())[:8]

        result = {
            "task_id": task_id,
            "task": task,
            "status": "running",
            "plan": [],
            "steps": [],
            "result": "",
            "iterations": 0,
            "errors": []
        }

        # === PHASE 1: PLAN ===
        await self._notify_step(task_id, 1, "PLAN", "Creating execution plan...")
        plan = await self._create_plan(task, context)
        result["plan"] = plan

        if self._cancelled:
            result["status"] = "cancelled"
            return result

        # === PHASE 2-5: EXECUTE LOOP ===
        for i, step in enumerate(plan):
            if self._cancelled:
                result["status"] = "cancelled"
                break

            if i >= self.MAX_ITERATIONS:
                result["errors"].append("Max iterations reached")
                result["status"] = "max_iterations"
                break

            result["iterations"] = i + 1

            # RESEARCH sub-phase if needed
            if step.get("needs_research"):
                await self._notify_step(task_id, i+1, "RESEARCH", f"Researching: {step['description']}")
                research = await self._do_research(step)
                step["research_result"] = research

            # EXECUTE
            await self._notify_step(task_id, i+1, "EXECUTE", step["description"])
            try:
                step_result = await self._execute_step(step)
                step["result"] = step_result
                step["status"] = "success"
            except Exception as e:
                step["result"] = str(e)
                step["status"] = "failed"
                result["errors"].append(f"Step {i+1}: {e}")

                # REFLECT & RETRY
                await self._notify_step(task_id, i+1, "REFLECT", f"Step failed. Analyzing...")
                fix = await self._attempt_fix(step, str(e))
                if fix:
                    step["fix_attempt"] = fix
                    try:
                        step_result = await self._execute_step(fix)
                        step["result"] = step_result
                        step["status"] = "success_after_retry"
                    except Exception as e2:
                        step["result"] += f"\nRetry failed: {e2}"
                        step["status"] = "failed_after_retry"
                        result["errors"].append(f"Step {i+1} retry: {e2}")

            result["steps"].append(step)

            # OBSERVE — check if we need to adjust plan
            if i < len(plan) - 1:
                should_adjust = await self._observe_and_adjust(result)
                if should_adjust:
                    new_steps = await self._adjust_plan(task, result)
                    plan = plan[:i+1] + new_steps

        # === PHASE 6: REPORT ===
        if result["status"] == "running":
            result["status"] = "completed" if not result["errors"] else "completed_with_errors"

        await self._notify_step(task_id, result["iterations"], "REPORT", "Generating final report...")
        result["result"] = await self._generate_report(result)

        return result

    def cancel(self) -> None:
        """Cancel the autonomous loop."""
        self._cancelled = True

    async def _create_plan(self, task: str, context: str) -> List[Dict]:
        """Ask LLM to create an execution plan."""
        prompt = f"""You are Lucienne (CENGO), an autonomous execution agent.

Task: {task}
Context: {context}

Create a step-by-step execution plan. Return ONLY a JSON array:
[
  {{"step": 1, "description": "...", "action": "code|shell|search|read|write", "needs_research": false, "target": "filename or URL"}},
  ...
]

Rules:
- Max 10 steps
- Each step must have: step, description, action, needs_research (bool), target
- Action must be one of: code, shell, search, read, write, github, mcp
- Be specific about filenames and commands
"""
        response = await self.llm(prompt)
        try:
            # Extract JSON from response
            json_str = response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0]
            plan = json.loads(json_str.strip())
            if isinstance(plan, list):
                return plan
        except Exception:
            pass

        # Fallback: single-step plan
        return [{"step": 1, "description": task, "action": "code", "needs_research": False, "target": ""}]

    async def _do_research(self, step: Dict) -> str:
        """Execute research for a step."""
        if step["action"] == "search":
            return await self.tool("web_search", {"query": step.get("target", step["description"])})
        elif step["action"] == "read":
            return await self.tool("read_file", {"path": step.get("target", "")})
        elif step["action"] == "github":
            return await self.tool("github", {"action": "info", "repo": step.get("target", "")})
        return ""

    async def _execute_step(self, step: Dict) -> str:
        """Execute a single step."""
        action = step["action"]
        target = step.get("target", "")
        desc = step["description"]

        if action == "code":
            return await self.tool("execute_code", {"description": desc, "language": "python"})
        elif action == "shell":
            return await self.tool("execute_shell", {"command": target or desc})
        elif action == "write":
            return await self.tool("write_file", {"path": target, "content": desc})
        elif action == "read":
            return await self.tool("read_file", {"path": target})
        elif action == "search":
            return await self.tool("web_search", {"query": target or desc})
        elif action == "github":
            return await self.tool("github", {"action": "execute", "command": desc})
        elif action == "mcp":
            return await self.tool("mcp", {"tool": target, "params": {}})
        else:
            return await self.tool("execute_code", {"description": desc, "language": "python"})

    async def _attempt_fix(self, step: Dict, error: str) -> Optional[Dict]:
        """Ask LLM how to fix a failed step."""
        prompt = f"""Step failed:
Description: {step['description']}
Action: {step['action']}
Target: {step.get('target', '')}
Error: {error}

Provide a corrected step as JSON:
{{"description": "...", "action": "...", "target": "..."}}

If unfixable, return: {{"unfixable": true}}
"""
        response = await self.llm(prompt)
        try:
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]
            fix = json.loads(response.strip())
            if fix.get("unfixable"):
                return None
            return {**step, **fix}
        except Exception:
            return None

    async def _observe_and_adjust(self, result: Dict) -> bool:
        """Check if plan needs adjustment mid-flight."""
        # Simple heuristic: if last step failed, definitely adjust
        if result["steps"] and result["steps"][-1].get("status", "").startswith("failed"):
            return True
        return False

    async def _adjust_plan(self, task: str, result: Dict) -> List[Dict]:
        """Generate new steps based on current progress."""
        prompt = f"""Task: {task}
Progress so far: {json.dumps(result['steps'], indent=2)}

The plan needs adjustment. Generate additional steps as JSON array to complete the task.
Return [] if task is actually complete.
"""
        response = await self.llm(prompt)
        try:
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]
            new_steps = json.loads(response.strip())
            if isinstance(new_steps, list):
                return new_steps
        except Exception:
            pass
        return []

    async def _generate_report(self, result: Dict) -> str:
        """Generate human-readable report."""
        prompt = f"""Summarize this execution result for the user in Indonesian (technical terms in English):

Task: {result['task']}
Status: {result['status']}
Iterations: {result['iterations']}
Steps: {json.dumps(result['steps'], indent=2)}
Errors: {result['errors']}

Format:
🌙 **Task Report: {result['task_id']}**
Status: {result['status']}

**Summary:** (2-3 sentences)

**Steps Executed:**
1. ...

**Result:**
...

**Next Steps / Suggestions:**
...
"""
        return await self.llm(prompt)

    async def _notify_step(self, task_id: str, step_num: int, phase: str, message: str) -> None:
        if self.on_step:
            await self.on_step(step_num, phase, message)
