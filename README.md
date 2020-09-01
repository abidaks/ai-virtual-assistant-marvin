# Multilingual Artificial Intelligence Virtual Assistant Marvin like Alexa and Siri

 It is a multilingual virtual assistant Artificial Intelligence program like alexa and siri, developed using google api's.
 This virtual assistant supports multiple languages, currently i added code for english and arabic, you can add more.

## Installing this module

### Local installation

> **Requirements**
>
> This project has been tested in Ubuntu 18.04 with Python 3.6.5. Further package requirements are described in the
> `requirements.txt` file.

```
> git clone https://github.com/abidaks/ai-virtual-assistant-marvin
> cd ai-virtual-assistant-marvin
```


## Installing dependencies

run below command to install dependencies
```

> pip install requirements.txt
```

You also need google services for the translation, its free to try.

For more details more details
[Google speech to text service](https://cloud.google.com/speech-to-text)

Create a free account and download the api credentials provided by google and replace them under "google/google-credentials.json"

## Running Marvin

Before you run marvin make sure that you have a microfone attached to your pc or laptop, also replaced the google api credentials.

Use below command to run marvin
```
python marvin.py
```

## How Marvin works?
Once you run marvin it will start accepting commands.

To trigger marvin you have to say

"hi marvin"

When it hear you it will play a bell sound.

then you can ask anything.

To change language from english to arabic

first you have to say

"hi marvin"

When it hear you it will play a bell sound.

Then you can ask marvin to change language

"Change language to arabic"
or
"Change language to english"

Similarly you can add your own commands and perform tasks accordingly.



## Speech Recognition
The speech recognition is done using tensorflow and keras. I included already trained model for speech recognition.
I will add another repo to train your own model.

## License

* [GNU General Public License](http://www.gnu.org/licenses/)
