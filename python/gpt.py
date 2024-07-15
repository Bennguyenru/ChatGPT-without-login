import time
import asyncio
import argparse
from playwright.async_api import async_playwright

class GPT:
    def __init__(self, prompt, streaming=True, proxy=None, session_token=None):
        self.prompt = prompt
        self.streaming = streaming
        self.proxy = proxy
        self.session_token = session_token
        self.browser = None
        self.page = None
        self.session_active = True
        self.last_message_id = None
        self.message_count = 0

    async def start(self):
        async with async_playwright() as p:
            launch_options = {'headless': True}
            if self.proxy:
                launch_options['proxy'] = {
                    'server': self.proxy
                }
            self.browser = await p.firefox.launch(**launch_options)
            context_options = {
                'user_agent': "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3.1 Mobile/15E148 Safari/604.1"
            }
            context = await self.browser.new_context(**context_options)

            self.page = await context.new_page()
            await self.page.goto('https://chatgpt.com', wait_until='networkidle')

            if self.session_token:
                await context.add_cookies([{
                    'name': '__Secure-next-auth.session-token',
                    'value': self.session_token,
                    'domain': '.chatgpt.com',
                    'path': '/',
                    'secure': True,
                    'httpOnly': True,
                    'sameSite': 'Lax'
                }])

            await self.page.reload(wait_until='networkidle')
            await self.handle_prompt(self.prompt)

            while self.session_active:
                next_prompt = input("\n►: ")
                if next_prompt.lower() == 'exit':
                    self.session_active = False
                    break
                await self.handle_prompt(next_prompt)

    async def handle_prompt(self, prompt_text):
        prompt_textarea = await self.page.query_selector('#prompt-textarea')
        if prompt_textarea is None:
            print("Cannot find the prompt input on the webpage.\nPlease check whether you have access to chatgpt.com without logging in via your browser.")
            self.session_active = False
            await self.close()
            return 
        
        await self.page.evaluate(f'document.querySelector("#prompt-textarea").value = "{prompt_text[:-1]}"')
        await self.page.type('#prompt-textarea', prompt_text[-1])
        
        try:
            fruitjuice_send_button = await self.page.evaluate('document.querySelector(\'[data-testid="fruitjuice-send-button"]\') !== null')
            send_button = await self.page.evaluate('document.querySelector(\'[data-testid="send-button"]\') !== null')

            if fruitjuice_send_button:
                await self.page.click('[data-testid="fruitjuice-send-button"]')
            elif send_button:
                await self.page.click('[data-testid="send-button"]')
            else:
                print("Neither send button is present")
        except Exception as e:
            print(f"Failed to click the send button: {str(e)}")

        await self.wait_for_and_print_new_response()

    async def wait_for_and_print_new_response(self):
        await self.wait_for_initial_response()
        await self.handle_streaming_response()

    async def wait_for_initial_response(self):
        start_time = time.time()
        timeout = 30
        while (time.time() - start_time) < timeout:
            
            while True:
                assistant_messages = await self.page.query_selector_all('div[data-message-author-role="assistant"]')
                current_message_count = len(assistant_messages)
                if current_message_count > self.message_count:
                    break
                await asyncio.sleep(0.1)


            if assistant_messages:
                last_message = assistant_messages[-1]
                is_thinking = await last_message.query_selector('.result-thinking')
                if not is_thinking:
                    self.last_message_id = await self.page.evaluate('(element) => element.getAttribute("data-message-id")', last_message)
                    self.message_count = current_message_count
                    return
            await asyncio.sleep(0.1)
        print("Timed out waiting for the initial response.")

    async def handle_streaming_response(self):
        previous_text = ""
        complete_response = ""
        new_content_detected = False
        while not new_content_detected:
            assistant_messages = await self.page.query_selector_all('div[data-message-author-role="assistant"]')
            if assistant_messages:
                last_message = assistant_messages[-1]
                current_message_id = await self.page.evaluate('(element) => element.getAttribute("data-message-id")', last_message)
                
                if current_message_id == self.last_message_id:
                    current_text = await self.page.evaluate('(element) => element.textContent', last_message)
                    if current_text != previous_text:
                        if self.streaming:
                            print(current_text[len(previous_text):], end='', flush=True)
                        else:
                            complete_response += current_text[len(previous_text):]

                    previous_text = current_text
                    is_streaming = await last_message.query_selector('.result-streaming')
                    if not is_streaming:
                        new_content_detected = True
                else:
                    self.last_message_id = current_message_id
            await asyncio.sleep(0.1)
        
        if not self.streaming:
            print(complete_response.rstrip())

    async def close(self):
        # Before calling close, check if the object is not None
        if self.page is not None:
            await self.page.close()
        await self.browser.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='ChatGPT without login')
    parser.add_argument('-p', '--prompt', type=str, default="Hello, GPT", help='The initial prompt text to send to ChatGPT')
    parser.add_argument('-x', '--proxy', type=str, help='Proxy server to use, e.g. http://proxyserver:port')
    parser.add_argument('-ns', '--no-streaming', dest='streaming', action='store_false', help='Disable streaming of ChatGPT responses')
    parser.add_argument('-st', '--session-token', type=str, help='Session token for __Secure-next-auth.session-token cookie')
    args = parser.parse_args()

    async def main():
        session = GPT(args.prompt, args.streaming, args.proxy, args.session_token)
        try:
            await session.start()
        except KeyboardInterrupt:
            print("Interrupted by user, closing...")
        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            # Similarly, when closing the session, ensure it's not None
            if session is not None:
                await session.close()

    asyncio.run(main())
    
    // Fixed version of test_implementation.js

    const { GPT } = require('./gpt.js');

    (async () => {
        try {
            // create gpt instance & send initial prompt
            const gptSession = new GPT("Tell me a joke.", true);

            await gptSession.start();
            
            console.log("\n -- asking GPT to explain the joke -- \n");
            // Fixed: Ensuring the prompt handling method is correctly awaited before proceeding
            await gptSession.handlePrompt("Explain the joke.");

            // gracefully close the session
            await gptSession.close();
        } catch (error) {
            console.error("Error in GPT session:", error);
        }
    })();