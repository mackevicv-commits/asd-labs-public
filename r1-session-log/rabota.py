#!/usr/bin/env python3
import sys


class Stack:
    def __init__(self):
        self._items = []

    def push(self, value):
        self._items.append(value)

    def pop(self):
        return self._items.pop()

    def empty(self):
        return len(self._items) == 0


def is_valid_name(name):
    if not name:
        return False
    for ch in name:
        if not (ch.isascii() and ch.isalnum()):
            return False
    return True


def parse_event(line):
    tokens = line.split()
    if not tokens:
        return "skip", None
    if len(tokens) != 2:
        return None, None
    kind, name = tokens
    if kind not in ("LOGIN", "LOGOUT"):
        return None, None
    if not is_valid_name(name):
        return None, None
    return kind, name


class SessionAnalyzer:
    def __init__(self):
        self.stacks = {}
        self.completed = 0
        self.active = 0
        self.peak = 0
        self.peak_line = 0
        self.scan_errors = []
        self.final_errors = []

    def handle_login(self, name, line_no):
        if name not in self.stacks:
            self.stacks[name] = Stack()
        self.stacks[name].push(line_no)
        self.active += 1
        if self.active > self.peak:
            self.peak = self.active
            self.peak_line = line_no

    def handle_logout(self, name, line_no):
        stack = self.stacks.get(name)
        if stack is None or stack.empty():
            self.scan_errors.append((line_no, "logout_without_login"))
            return
        stack.pop()
        self.completed += 1
        self.active -= 1

    def process_line(self, line_no, line):
        kind, name = parse_event(line)
        if kind == "skip":
            return
        if kind is None:
            self.scan_errors.append((line_no, "bad_event"))
            return
        if kind == "LOGIN":
            self.handle_login(name, line_no)
        else:
            self.handle_logout(name, line_no)

    def finish(self):
        unfinished = []
        for stack in self.stacks.values():
            while not stack.empty():
                unfinished.append(stack.pop())
        unfinished.sort()
        for line_no in unfinished:
            self.final_errors.append((line_no, "session_not_closed"))

    def build_output(self):
        lines = []
        for line_no, code in self.scan_errors:
            lines.append(f"ERROR {line_no} {code}")
        for line_no, code in self.final_errors:
            lines.append(f"ERROR {line_no} {code}")
        lines.append(f"SESSIONS {self.completed}")
        return "\n".join(lines) + "\n"


def read_lines(path):
    with open(path, "rb") as f:
        for raw in f:
            yield raw.decode("utf-8", "replace").rstrip("\r\n")


def main():
    if len(sys.argv) != 3:
        sys.stderr.write("usage: rabota.py input.txt output.txt\n")
        sys.exit(2)

    input_path, output_path = sys.argv[1], sys.argv[2]
    analyzer = SessionAnalyzer()

    for line_no, line in enumerate(read_lines(input_path), start=1):
        try:
            analyzer.process_line(line_no, line)
        except Exception:
            analyzer.scan_errors.append((line_no, "bad_event"))

    analyzer.finish()

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(analyzer.build_output())


def bench(input_path, repeats=5):
    import time

    with open(input_path, "rb") as f:
        for _ in f:
            pass

    times = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        analyzer = SessionAnalyzer()
        for line_no, line in enumerate(read_lines(input_path), start=1):
            try:
                analyzer.process_line(line_no, line)
            except Exception:
                analyzer.scan_errors.append((line_no, "bad_event"))
        analyzer.finish()
        t1 = time.perf_counter()
        times.append(t1 - t0)

    times.sort()
    median = times[len(times) // 2]
    print(f"{input_path}: median={median:.6f} min={times[0]:.6f} max={times[-1]:.6f}")


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--bench":
        bench(sys.argv[2])
    else:
        main()