import random
import time


class AIReviewer:
    """Generates contextual, unique daily task and productivity reviews."""

    def _fmt(self, seconds):
        h = seconds // 3600
        m = (seconds % 3600) // 60
        if h > 0 and m > 0:
            return f"{h}h {m}m"
        elif h > 0:
            return f"{h}h"
        return f"{m}m"

    def generate_review(self, tasks, screen_time, social_time, social_limit,
                        screen_limit, top_apps, usage_by_category,
                        health_status, streak, weekly_goals=None):
        rng = random.Random(time.time())

        completed = [t for t in tasks if t.get("completed")]
        missed = [t for t in tasks if not t.get("completed")]
        total = len(tasks)
        done = len(completed)
        goals = weekly_goals or []

        parts = []

        if total == 0 and screen_time < 60:
            openers = [
                "Your day is just getting started. Add tasks and let me track your progress.",
                "No tasks set yet. Define your priorities and I'll review your performance.",
                "Blank slate today. Set your tasks and I'll give you a full analysis later.",
            ]
            return rng.choice(openers)

        if total > 0:
            p = self._task_analysis(rng, completed, missed, total, done)
            if p:
                parts.append(p)

        if total > 0 and screen_time > 300:
            p = self._time_worth(rng, completed, missed, screen_time,
                                 screen_limit, usage_by_category)
            if p:
                parts.append(p)

        if missed:
            p = self._missed_analysis(rng, missed, social_time)
            if p:
                parts.append(p)

        if social_time > 300:
            p = self._social_analysis(rng, social_time, social_limit)
            if p:
                parts.append(p)

        parts.append(self._verdict(rng, done, total, health_status, streak,
                                   screen_time, screen_limit))

        # Sometimes add a short motivational nudge about self-improvement
        nudge = self._motivation(rng, completed, missed, goals, streak,
                                 health_status, done, total)
        if nudge:
            parts.append(nudge)

        return " ".join(parts)

    def _task_analysis(self, rng, completed, missed, total, done):
        rate = done / total if total > 0 else 0

        if rate == 1.0:
            t = [
                f"Perfect execution — all {total} tasks completed. That's elite-level discipline.",
                f"You cleared every single task ({total}/{total}). Days like this compound into real results.",
                f"All {total} tasks done. No loose ends, no excuses — peak productivity.",
                f"Flawless completion. {total} for {total}. Your future self will thank you for today.",
                f"Complete sweep — {total} tasks, {total} wins. You're operating at full capacity.",
                f"Every task checked off. {total}/{total}. This is what a focused day looks like.",
            ]
        elif rate >= 0.7:
            names = ", ".join(f'"{c["title"]}"' for c in completed[:2])
            t = [
                f"Strong showing — {done}/{total} tasks including {names}. Solid momentum.",
                f"You tackled {done} out of {total} tasks today. Good prioritization on what mattered.",
                f"{done}/{total} completed. You focused on the right ones: {names}.",
                f"Productive day with {done}/{total} tasks done. The key wins are in the bag.",
                f"{done} of {total} tasks finished — you hit the important ones like {names}.",
            ]
        elif rate > 0:
            t = [
                f"Only {done}/{total} tasks completed today. There's room to push harder tomorrow.",
                f"{done} out of {total} — you started but didn't finish strong. Commit fully tomorrow.",
                f"Partial completion: {done}/{total}. Identify what blocked you and eliminate it.",
                f"You got {done} done but left {total - done} behind. What got in the way?",
            ]
        else:
            t = [
                f"Zero tasks completed out of {total}. This day was a missed opportunity.",
                f"None of your {total} tasks got done today. Time to reassess your approach.",
                f"0/{total} tasks completed. Something needs to change — what's holding you back?",
                f"All {total} tasks untouched. Tomorrow, start with the smallest one to build momentum.",
            ]

        return rng.choice(t)

    def _time_worth(self, rng, completed, missed, screen_time, screen_limit,
                    usage):
        prod_time = usage.get("productivity", 0)
        social_cat = usage.get("social_media", 0)
        entertainment = usage.get("entertainment", 0) + usage.get("gaming", 0)
        prod_pct = (prod_time / screen_time * 100) if screen_time > 0 else 0
        waste_time = social_cat + entertainment

        if len(completed) > 0 and prod_pct > 50:
            name = completed[0]["title"]
            t = [
                f'Your {self._fmt(prod_time)} of productive time aligns well with completing "{name}". Time well invested.',
                f"With {int(prod_pct)}% of screen time being productive, your completed tasks genuinely earned their checkmarks.",
                f"The ratio of productive work ({self._fmt(prod_time)}) to total screen time validates today's effort.",
                f"{int(prod_pct)}% productivity ratio — the tasks you finished were backed by real focused work.",
            ]
        elif len(completed) > 0 and waste_time > prod_time:
            t = [
                f"Tasks got done, but {self._fmt(waste_time)} went to distractions vs {self._fmt(prod_time)} of focused work. Efficiency could improve.",
                f"You completed tasks, but at what cost? More time on entertainment ({self._fmt(waste_time)}) than productive work ({self._fmt(prod_time)}).",
                f"The tasks you finished are valid wins, but {self._fmt(waste_time)} on distractions suggests fragmented focus.",
            ]
        elif len(completed) == 0 and screen_time > 3600:
            t = [
                f"You spent {self._fmt(screen_time)} on screen with zero task completion. That time didn't move the needle.",
                f"No tasks completed despite {self._fmt(screen_time)} of screen time. It wasn't invested — it was consumed.",
                f"{self._fmt(screen_time)} of screen time, zero tasks done. The screen was on, but progress wasn't.",
            ]
        else:
            return None

        return rng.choice(t)

    def _missed_analysis(self, rng, missed, social_time):
        names = [m["title"] for m in missed]

        if len(missed) == 1:
            name = names[0]
            if social_time > 1800:
                t = [
                    f'You missed "{name}" — and spent {self._fmt(social_time)} on social media. That trade-off might not be worth it.',
                    f'"{name}" didn\'t get done. With {self._fmt(social_time)} on social media, you had the time — it was a choice.',
                    f'The one task you missed — "{name}" — could have fit in the time spent scrolling ({self._fmt(social_time)}).',
                ]
            else:
                t = [
                    f'You left "{name}" incomplete. Make it your first priority tomorrow.',
                    f'"{name}" is still pending. Uncompleted tasks accumulate mental weight — close it out.',
                    f'One task missed: "{name}". If it matters enough to list, it matters enough to finish.',
                    f'"{name}" carried over. Don\'t let it become a habit — attack it first thing.',
                ]
        elif len(missed) <= 3:
            ns = " and ".join(f'"{n}"' for n in names[:3])
            t = [
                f"You left {ns} unfinished. Each represents a commitment you made to yourself today.",
                f"Missed tasks: {ns}. Prioritize these first thing tomorrow to avoid a backlog spiral.",
                f"{len(missed)} tasks incomplete: {ns}. Tomorrow, tackle the hardest one first.",
                f"Still pending: {ns}. Carrying tasks forward erodes trust in your own plans.",
            ]
        else:
            t = [
                f"{len(missed)} tasks missed. You may be overcommitting — try fewer, more focused tasks.",
                f"With {len(missed)} incomplete tasks, consider whether you're setting realistic daily goals.",
                f"{len(missed)} unfinished tasks. Quality over quantity — set 3-5 critical tasks instead.",
                f"Too many tasks left undone ({len(missed)}). Trim tomorrow's list to what truly matters.",
            ]

        return rng.choice(t)

    def _social_analysis(self, rng, social_time, social_limit):
        pct = social_time / social_limit if social_limit > 0 else 0

        if pct >= 1.0:
            t = [
                f"Social media limit exceeded ({self._fmt(social_time)}/{self._fmt(social_limit)}). Every minute over is borrowed from tomorrow's goals.",
                f"You blew past your social media budget. {self._fmt(social_time)} consumed against a {self._fmt(social_limit)} limit.",
                f"Over the social limit by {self._fmt(social_time - social_limit)}. That overflow came at the expense of something else.",
            ]
        elif pct > 0.7:
            t = [
                f"Social media usage is high at {self._fmt(social_time)} — approaching your {self._fmt(social_limit)} limit. Stay vigilant.",
                f"You used {int(pct * 100)}% of your social media allowance. Close to the edge — be intentional.",
            ]
        elif pct < 0.3:
            t = [
                f"Excellent social media discipline — only {self._fmt(social_time)} used. That restraint fuels real productivity.",
                f"Minimal social media usage ({self._fmt(social_time)}). You're keeping distractions in check. Impressive.",
                f"Only {int(pct * 100)}% of your social budget used. That's the discipline of someone who gets things done.",
            ]
        else:
            return None

        return rng.choice(t)

    def _verdict(self, rng, done, total, health_status, streak,
                 screen_time, screen_limit):
        score = 0
        if total > 0:
            score += (done / total) * 40
        if health_status == "healthy":
            score += 30
        elif health_status == "moderate":
            score += 15
        if streak > 0:
            score += min(streak * 5, 30)

        if score >= 80:
            v = [
                "Overall: Outstanding day. Keep this energy — momentum is everything.",
                "Verdict: You showed up and delivered. Maintain this standard.",
                "Bottom line: Today was a win. Stack another one tomorrow.",
                "Assessment: High-performance day. This is the trajectory you want.",
                "Final take: Exceptional execution. This is what your best looks like.",
                "Summary: Today proved you can perform. Now make it the norm.",
            ]
        elif score >= 50:
            v = [
                "Overall: Decent day with clear room for improvement.",
                "Verdict: Not bad, not great. Tomorrow is a chance to level up.",
                "Bottom line: Average performance. You're capable of more — prove it.",
                "Assessment: Acceptable, but you didn't push your limits today.",
                "Final take: You did the minimum. Aim higher tomorrow.",
            ]
        else:
            v = [
                "Overall: Tough day. Reset tonight and come back stronger.",
                "Verdict: Below your potential. Use this as fuel, not frustration.",
                "Bottom line: Off day. Every champion has them — what matters is tomorrow.",
                "Assessment: Not your best. Acknowledge it, learn from it, move on.",
                "Final take: Today didn't go to plan. Tomorrow is a clean slate — own it.",
            ]

        return rng.choice(v)

    def _motivation(self, rng, completed, missed, goals, streak,
                    health_status, done, total):
        # ~60% chance to include a motivational nudge
        if rng.random() > 0.6:
            return None

        goal_done = [g for g in goals if g.get("completed")]
        goal_pending = [g for g in goals if not g.get("completed")]

        pool = []

        # Goal-aware nudges
        if goal_pending:
            g = rng.choice(goal_pending)
            name = g.get("title", "your goal")
            pool += [
                f'💡 Remember why you set "{name}" — every small step counts.',
                f'🎯 "{name}" is still in play. One focused push could change everything.',
                f'⚡ Your goal "{name}" won\'t complete itself — but you can. Start small.',
                f'🔥 Keep "{name}" in sight. Progress beats perfection.',
                f'💪 "{name}" is waiting. Today\'s effort is tomorrow\'s result.',
            ]

        if goal_done and len(goal_done) == len(goals) and goals:
            pool += [
                "🏆 All weekly goals crushed. You're proof that consistency works.",
                "✨ Every goal checked off — you're building something real.",
                "🚀 Weekly goals complete. Raise the bar next week.",
            ]
        elif goal_done:
            g = rng.choice(goal_done)
            name = g.get("title", "a goal")
            pool += [
                f'✅ You nailed "{name}". That momentum is yours — use it.',
                f'🌟 Completing "{name}" shows you mean business. Keep that energy.',
            ]

        # Task-aware motivational nudges
        if done > 0 and total > 0 and done == total:
            pool += [
                "🧠 Perfect days don't happen by accident. You chose this.",
                "💎 Discipline is a muscle — and yours is getting stronger.",
                "🔑 Today's consistency is tomorrow's freedom.",
            ]
        elif done > 0:
            pool += [
                "📈 Progress isn't linear, but you're moving forward.",
                "🌱 Small wins stack up. Don't underestimate what you did today.",
                "⏳ You can't get today back, but you made some of it count.",
            ]
        elif total > 0:
            pool += [
                "🛤️ Rough days build resilience. Show up again tomorrow.",
                "💡 Failure isn't falling down — it's not getting back up.",
                "🔄 Reset, refocus, restart. You've done it before.",
            ]

        # Streak-based
        if streak >= 7:
            pool += [
                f"🔥 {streak} days strong. You're not just trying — you're becoming.",
                f"⚡ {streak}-day streak. Habits this consistent change lives.",
            ]
        elif streak >= 3:
            pool += [
                f"🔥 {streak} days in a row. Momentum is building — don't break the chain.",
                f"💪 {streak}-day streak. You're proving you can show up.",
            ]
        elif streak == 0 and total > 0:
            pool += [
                "🌅 No streak yet — today is day one if you want it to be.",
                "🏁 Every streak starts with a single day. Make tomorrow count.",
            ]

        # General short motivational
        pool += [
            "🧭 You're closer than you think. Keep going.",
            "💬 The best investment you'll ever make is in yourself.",
            "🌊 Growth is uncomfortable. That's how you know it's working.",
            "🎯 Focus on who you're becoming, not just what you're doing.",
            "⭐ The person you'll be in a year is built by days like today.",
        ]

        return rng.choice(pool)
