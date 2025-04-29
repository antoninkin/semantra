# This script builds the Svelte frontend, copies the build to the Flask static folder,
# and runs the Flask app. It also handles errors and provides real-time output for long-running commands.
import subprocess
import shutil
import os
import sys
import time


def run_command(command, cwd=None, continuous_output=False):
    """
    Runs a shell command, prints output in real-time.
    Set continuous_output=True for long-running commands like servers.
    """
    print(f"Running: {command}")
    process = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        cwd=cwd,
    )

    if continuous_output:
        # For continuously running processes (like servers)
        # Use non-blocking reads to show output in real-time
        import threading

        def print_output(stream, prefix=''):
            for line in iter(stream.readline, ''):
                if line:
                    print(f"{prefix}{line}", end='')

        # Start threads to read output continuously
        stdout_thread = threading.Thread(target=print_output, args=(process.stdout, ''))
        stderr_thread = threading.Thread(target=print_output, args=(process.stderr, ''))
        stdout_thread.daemon = True
        stderr_thread.daemon = True
        stdout_thread.start()
        stderr_thread.start()

        return process  # Return the process so caller can decide when to terminate
    else:
        # For commands that complete (like build commands)
        for line in process.stdout:
            print(line, end="")
        for line in process.stderr:
            print(line, end="")

        process.wait()

        # Raise an error if the command failed
        if process.returncode != 0:
            raise RuntimeError(
                f"Command failed with exit code {process.returncode}: {command}"
            )


def find_python_command():
    """Checks if 'python' or 'python3' is available and returns the correct command."""
    for cmd in ["python", "python3"]:
        try:
            subprocess.run(
                [cmd, "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
            return cmd
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue
    raise RuntimeError("Python is not installed or not found in PATH.")


def build_frontend():
    print("📦 Building Svelte frontend...")
    run_command("npm run build", cwd="client")
    print("✅ Build complete.")


def copy_folder():
    """Copies the build from 'client/public' to Flask static folder."""
    src_dir = os.path.join("client", "public")
    dst_dir = os.path.join("src", "semantra", "client_public")

    print("🚚 Copying build to Flask static folder...")
    print("Looking for:", os.path.abspath(src_dir))
    print("Destination:", os.path.abspath(dst_dir))
    if not os.path.exists(src_dir):
        print("❌ Source directory does not exist. Did the build fail?")
        return

    if os.path.exists(dst_dir):
        shutil.rmtree(dst_dir)
    shutil.copytree(src_dir, dst_dir)
    print("✅ Copy complete.")


def run_flask_app():
    """Runs the Flask app."""
    python_cmd = find_python_command()
    flask_command = f"{python_cmd} {os.path.join('src', 'semantra', 'semantra.py')}"

    print(f"🚀 Starting Flask app with command: {flask_command}")
    # Use continuous_output=True for the Flask server
    server_process = run_command(flask_command, continuous_output=True)

    try:
        # Keep the script running while the server is running
        while server_process.poll() is None:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n⚠️ Server interrupted. Shutting down...")
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
            print("✅ Server shut down gracefully.")
        except subprocess.TimeoutExpired:
            print("⚠️ Server didn't shut down. Killing...")
            server_process.kill()


def main():
    if '--copy_folder' in sys.argv:
        copy_folder()
    else:
        build_frontend()
        copy_folder()

    run_flask_app()


if __name__ == "__main__":
    main()