Project Workflow

This version of BinPj has been migrated from Node.js to Python with an updated controller logic. The system processes inputs from LineOA to control waste segregation via ESP32.

#Input Handling

The server receives data from LineOA in two formats:

    Text: Direct string input from the user.

    Image: Photos sent by the user for classification.

#Processing Logic

The controller handles the input based on its type:

    If Text:

        Scans Keywords.json for a match.

        Identifies the corresponding Bin Color.

        Calls find_bin() to retrieve the specific Bin Number.

    If Image:

        Processes the image to find the highest probability class.

        Threshold Check: If probability > 0.7 (70%):

            Matches the result with Keywords.json.

            Retrieves Bin Color and executes find_bin() for the Bin Number.

        If probability ≤ 0.7: The input is ignored or rejected (Safety check).

#Hardware Integration

Once the Bin Number is determined, the Python server sends a signal to the ESP32, which triggers the corresponding Servo Motor to open the bin.