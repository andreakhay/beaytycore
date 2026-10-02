import dotenv from 'dotenv';
dotenv.config({ path: '.env.local' });

const test = async () => {
  const response = await fetch("https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0", {
    headers: { Authorization: `Bearer ${process.env.HUGGINGFACE_API_KEY}` },
    method: "POST",
    body: JSON.stringify({ inputs: "test" }),
  });
  console.log(response.status);
  console.log(await response.text());
};
test();
