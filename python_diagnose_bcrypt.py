import sys
import os

print(f"Current working directory: {os.getcwd()}")
print(f"Python version: {sys.version}")
print(f"Python executable: {sys.executable}")
print(f"Python path: {sys.path}")
print("-" * 30)

try:
    print("Attempting to import bcrypt directly...")
    import bcrypt
    print(f"Successfully imported bcrypt module: {bcrypt}")
    print(f"bcrypt module type: {type(bcrypt)}")
    print(f"bcrypt file location: {getattr(bcrypt, '__file__', 'Not found')}")
    print(
        f"bcrypt version via __version__: {getattr(bcrypt, '__version__', 'Not found')}")

    if hasattr(bcrypt, '__about__'):
        print(f"bcrypt.__about__ exists: {bcrypt.__about__}")
        print(f"bcrypt.__about__ type: {type(bcrypt.__about__)}")
        print(
            f"bcrypt version via __about__.__version__: {getattr(bcrypt.__about__, '__version__', 'Not found')}")
    else:
        print("bcrypt.__about__ does NOT exist")
    print("-" * 30)
except ImportError as e:
    print(f"Failed to import bcrypt directly: {e}")
    import traceback
    traceback.print_exc()
    print("-" * 30)
except Exception as e:
    print(f"Error inspecting bcrypt directly: {e}")
    import traceback
    traceback.print_exc()
    print("-" * 30)

try:
    print("Attempting to import from passlib and inspect its bcrypt handler...")
    # Importing a hash that uses bcrypt can trigger its backend loading
    from passlib.hash import bcrypt_sha256
    print(f"Successfully imported passlib.hash.bcrypt_sha256: {bcrypt_sha256}")

    from passlib.registry import get_crypt_handler
    handler = get_crypt_handler("bcrypt")
    print(f"Passlib bcrypt handler obtained: {handler}")

    if hasattr(handler, "_bcrypt") and handler._bcrypt is not None:
        print(f"Passlib's loaded _bcrypt module: {handler._bcrypt}")
        print(f"Passlib's _bcrypt module type: {type(handler._bcrypt)}")
        print(
            f"Passlib's _bcrypt file location: {getattr(handler._bcrypt, '__file__', 'Not found')}")
        print(
            f"Passlib's _bcrypt version via __version__: {getattr(handler._bcrypt, '__version__', 'Not found')}")
        if hasattr(handler._bcrypt, '__about__'):
            print(
                f"Passlib's _bcrypt.__about__ exists: {handler._bcrypt.__about__}")
            print(
                f"Passlib's _bcrypt.__about__ type: {type(handler._bcrypt.__about__)}")
            print(
                f"Passlib's _bcrypt version via __about__.__version__: {getattr(handler._bcrypt.__about__, '__version__', 'Not found')}")
        else:
            print("Passlib's _bcrypt.__about__ does NOT exist")
    elif hasattr(handler, "get_backend_mixin"):  # Alternative way to check for issues
        print("Passlib handler has get_backend_mixin. Attempting to call it.")
        try:
            mixin_module, backend_status = handler.get_backend_mixin()
            print(
                f"get_backend_mixin returned module: {mixin_module}, status: {backend_status}")
            if mixin_module and hasattr(mixin_module, "_bcrypt_module"):
                loaded_bcrypt_module = mixin_module._bcrypt_module
                print(f" bcrypt module from mixin: {loaded_bcrypt_module}")
                print(
                    f" bcrypt file from mixin: {getattr(loaded_bcrypt_module, '__file__', 'Not found')}")
                print(
                    f" bcrypt __version__ from mixin: {getattr(loaded_bcrypt_module, '__version__', 'Not found')}")
                if hasattr(loaded_bcrypt_module, '__about__'):
                    print(
                        f" bcrypt __about__.__version__ from mixin: {getattr(loaded_bcrypt_module.__about__, '__version__', 'Not found')}")
                else:
                    print(f" bcrypt __about__ from mixin: NOT FOUND")

        except Exception as mixin_e:
            print(f"Error calling or inspecting get_backend_mixin: {mixin_e}")
            traceback.print_exc()
    else:
        print("Passlib's bcrypt handler does not have a readily inspectable _bcrypt attribute or it's None, and no get_backend_mixin.")
    print("-" * 30)

except ImportError as e:
    print(f"Failed to import from passlib or get handler: {e}")
    import traceback
    traceback.print_exc()
    print("-" * 30)
except Exception as e:
    print(f"Error during passlib diagnostics: {e}")
    import traceback
    traceback.print_exc()
    print("-" * 30)

print("Diagnostic script finished.")
