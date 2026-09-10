"""A fixture that deliberately trips the high-severity dynamic_exec rule."""


def evaluate(expression):
    # pyobfus cannot safely obfuscate code reached through eval().
    return eval(expression)
