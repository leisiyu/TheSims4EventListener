from sims4.unified_keys_dict import UnifiedKeysDictimport randomimport timeimport tracemalloc
def _create_dict(k):
    keys = [f'key_{i}' for i in range(k)]
    return {key: random.random() for key in keys}

def generate_dicts(n, k):
    dicts = []
    for _ in range(n):
        d = _create_dict(k)
        dicts.append(d)
    return dicts

def generate_ukd(n, k):
    dicts = []
    for _ in range(n):
        d = _create_dict(k)
        ukd = UnifiedKeysDict(d, 'ukd_1')
        dicts.append(ukd)
    return dicts

class UnifiedKeysDictUnitTest:
    pass

def main():
    n = 40000
    k = 20
    TEST_UKD = True
    if TEST_UKD:
        ukd_status = 'Unified Keys Dict (Pure Python)'
    else:
        ukd_status = 'Regular Python dict'
    print('Test Mode: ' + ukd_status)
    tracemalloc.start()
    result = generate_ukd(n, k) if TEST_UKD else generate_dicts(n, k)
    (current, _) = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    print(f'Current memory usage: {current/1024} KB')
    start_time = time.perf_counter()
    result = generate_ukd(n, k) if TEST_UKD else generate_dicts(n, k)
    end_time = time.perf_counter()
    print(f'time creating: {end_time - start_time} sec')
    start_time = time.perf_counter()
    for d in result:
        for i in range(k):
            key = f'key_{i}'
            val = d[key]
    end_time = time.perf_counter()
    print(f'time accessing: {end_time - start_time} sec')
if __name__ == '__main__':
    import doctest
    doctest.testmod()
    main()