import dotenv from 'dotenv';
dotenv.config({ path: '.env.local' });

const test = async () => {
  try {
    const res = await fetch("https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0", {
      headers: { 
        "Authorization": `Bearer ${process.env.HUGGINGFACE_API_KEY}`,
        "Content-Type": "application/json"
      },
      method: "POST",
      body: JSON.stringify({ inputs: "A cat in a hat" }),
    });
    
    console.log("Status:", res.status);
    if (!res.ok) {
      console.log("Text:", await res.text());
    } else {
      console.log("Success! Blob size:", (await res.arrayBuffer()).byteLength);
    }
  } catch (err) {
    console.error("Fetch failed:", err);
  }
};
test();
