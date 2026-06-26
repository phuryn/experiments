def add(a, b):
    return a + b

def mul(a, b):
    # BUG: should multiply
    return a + b

if __name__ == "__main__":
    print("add(2,3)=", add(2, 3))
    print("mul(2,3)=", mul(2, 3))
