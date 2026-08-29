from app.graph import app

def main() -> None:
    print("Weather and Flight Agent")
    print("Type 'exit' to stop.\n")

    while True:
        request = input(
            "Describe your trip:\n> "
        ).strip()

        if request.lower() == "exit":
            return

        if not request:
            continue

        for _ in range(3):
            result = app.invoke(
                {
                    "user_request": request
                }
            )

            missing = result.get(
                "missing",
                [],
            )

            if not missing:
                print("\n" + result["answer"] + "\n")
                break

            print(
                "\nMissing information: "
                + ", ".join(missing)
            )

            extra_information = input(
                "Please provide it:\n> "
            )

            request += (
                "\nAdditional information: "
                + extra_information
            )
        else:
            print(
                "\nThe request is still incomplete.\n"
            )

if __name__ == "__main__":
    main()
