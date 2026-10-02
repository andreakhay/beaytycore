const test = async () => {
  const res = await fetch('http://localhost:3000/api/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ style: "Stiletto", color: "Crimson Red", design: "Matte finish" })
  });
  const data = await res.json();
  console.log(data);
};
test();
