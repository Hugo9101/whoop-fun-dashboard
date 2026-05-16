import os
from fetch import get_profile, get_sleep, get_recovery, get_workouts, get_cycles, refresh_access_token, load_tokens_from_db
from store import save_sleep, save_recovery, save_workouts, save_cycles, save_profile

def run():
    if os.getenv("CI"):
        load_tokens_from_db()
    refresh_access_token()

    profile  = get_profile()
    print(f"\n👤 Logged in as: {profile.get('first_name')} {profile.get('last_name')}\n")

    sleep    = get_sleep()
    recovery = get_recovery()
    workouts = get_workouts()
    cycles   = get_cycles()

    print()
    save_profile(profile)
    save_sleep(sleep)
    save_recovery(recovery)
    save_workouts(workouts)
    save_cycles(cycles)

    print("\n✅ Done")

if __name__ == "__main__":
    run()
