from math import factorial as math_factorial

class Calculator:
    BINARY_OPS = {"plus", "minus", "times", "divide", "pow"}
    UNARY_OPS = {"abs", "fact"}

    def __init__(self):
        self.history = {"STACK": [], "INDEPENDENT": []}
        self.function_map = {
            "plus": self.add,
            "minus": self.subtract,
            "times": self.multiply,
            "divide": self.divide,
            "pow": self.power,
            "abs": self.absolute,
            "fact": self.factorial
        }
        self.stack = list()

    def calc(self, args, operation, is_independent=True):
        """
        Preform calculation if it can be invoked
        :param args: arguments to preform the calculation
        :param operation: calculation operation
        :param is_independent: flag to indentify the type of calculation execution
        :return: if the operation was successful and the result.
        """
        op_original = operation
        operation = operation.lower()

        if operation not in self.function_map:
            return False, f"Error: unknown operation: {op_original}"

        expected_num_of_args = 2 if operation in self.BINARY_OPS else 1

        if not is_independent:
            args = self.stack[-1:-expected_num_of_args - 1:-1]

        if len(args) < expected_num_of_args:
            msg = f"Error: Not enough arguments to perform the operation {op_original}" if is_independent\
                else f"Error: cannot implement operation {op_original}. It requires {expected_num_of_args} arguments and the stack has only {len(self.stack)} arguments"
            return False, msg

        if len(args) > expected_num_of_args and is_independent:
            return False, f"Error: Too many arguments to perform the operation {op_original}"

        # operation succeeded (without considering spacial errors) so pop args from the stack
        if not is_independent:
            self.stack.pop()
            if operation in self.BINARY_OPS:
                self.stack.pop()

        if operation == "divide" and args[1] == 0:
            return False, "Error while performing operation Divide: division by 0"

        if operation == "fact" and args[0] < 0:
            return False, "Error while performing operation Factorial: not supported for the negative number"

        result = self.function_map.get(operation)(args)
        self.log_to_history(op_original, args, result, is_independent)

        return True, result

    def delete_from_stack(self, quantity_to_delete = 0):
        """
        Delete elements from the stack by a given quantity
        :param quantity_to_delete: number of elements to delete
        :return: if the operation was successful and the current stack size.
        """
        if quantity_to_delete > len(self.stack):
            return False, f"Error: cannot remove {quantity_to_delete} from the stack. It has only {len(self.stack)} arguments"
        for _ in range(quantity_to_delete):
            self.stack.pop()
        return True, len(self.stack)

    def log_to_history(self, operation, arguments, result, is_independent=False):
        """
        Log successful operation to history.
        :param operation: executed operation.
        :param arguments: arguments which the calculation was performed on.
        :param result: result of the calculation.
        :param is_independent: execution type the calculation was performed in.
        :return: None.
        """
        flavor = "INDEPENDENT" if is_independent else "STACK"
        self.history[flavor].append({"flavor": flavor, "operation": operation, "arguments": arguments, "result": result})

    def get_history(self, flavor = None):
        """
        Get the history of the calculations which was preformed by execution flavor.
        :param flavor: execution type the calculation was performed on.
        :return: All calculation from a given flavor. (if not supplied, return all when STACK are first)
        """
        if flavor:
            return self.history[flavor]
        else:
            return self.history.get("STACK") + self.history["INDEPENDENT"]

    def get_last_calc(self, flavor = None):
        return self.history.get(flavor)[-1]

    @staticmethod
    def add(args):
        """add two numbers together"""
        return sum(args)

    @staticmethod
    def subtract(args):
        """subtract two numbers together"""
        return args[0] - args[1]

    @staticmethod
    def multiply(args):
        """multiply two numbers together"""
        return args[0] * args[1]

    @staticmethod
    def divide(args):
        """divide two numbers together"""
        return args[0] // args[1]  # return only the integer part

    @staticmethod
    def power(args):
        """implement power calculation"""
        return args[0] ** args[1]

    @staticmethod
    def absolute(args):
        """calculate absolute value of a number"""
        return abs(args[0])

    @staticmethod
    def factorial(args):
        """calculate factorial of a number"""
        return math_factorial(args[0])
