import concurrent.futures


def pt(*funcs):
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        futures = [executor.submit(func) for func in funcs]
        for future in concurrent.futures.as_completed(futures):
            future.result()


def ptr(*funcs):
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(func) for func in funcs]
        results = []
        for future in futures:
            result = (
                future.result()
            )  # This will raise an exception if the future encountered one.
            results.append(result)
    return results


def pp(*func_args):
    with concurrent.futures.ProcessPoolExecutor(max_workers=2) as executor:
        for i in range(0, len(func_args), 2):
            futures = [
                executor.submit(func, *args) if args else executor.submit(func)
                for func, args in func_args[i : i + 2]
            ]
            concurrent.futures.wait(futures)
            for future in futures:
                future.result()
