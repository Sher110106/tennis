import os
import subprocess

def test_final_script():
    """Test the final.py script with a small sample of tournament data"""
    # Simple test data - just enough to verify stdin processing works
    sample_data = """
The Championships 2010
Qualifying Ladies' Singles
First Round
1. Kaia Kanepi [1].................................................................. (EST)
2. Olga Savchuk..................................................................... (UKR)
Second Round
K. Kanepi [1]..............................................6/1 7/5
    """
    
    print("Testing final.py with sample data...")
    try:
        # Run final.py with sample data as input
        result = subprocess.run(
            ["python", "final.py"],
            input=sample_data,  # No need to encode here - subprocess will handle it
            capture_output=True,
            text=True
        )
        
        print("Output from final.py:")
        print(result.stdout)
        
        if result.stderr:
            print("Errors:")
            print(result.stderr)
            
        # Check if output.csv was created
        if os.path.exists("output.csv"):
            print("Success! output.csv was created/updated.")
            with open("output.csv", "r") as f:
                lines = f.readlines()
                print(f"CSV contains {len(lines)} lines (including header)")
        else:
            print("Error: output.csv was not created")
            
        return result.returncode == 0
    except Exception as e:
        print(f"Error testing final.py: {e}")
        return False

if __name__ == "__main__":
    test_final_script()