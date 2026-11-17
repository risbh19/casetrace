# Legal corpus

`sections.json` contains section-level paraphrases for this synthetic training demo. The primary verification sources are linked in each record.

- [Bharatiya Nagarik Suraksha Sanhita, 2023](https://egazette.gov.in/WriteReadData/2023/250884.pdf)
- [Bharatiya Nyaya Sanhita, 2023](https://www.indiacode.nic.in/bitstream/123456789/20062/1/a2023-45.pdf)
- [Bharatiya Sakshya Adhiniyam, 2023](https://www.indiacode.nic.in/indiacode/bitstream/123456789/20063/1/aa202347.pdf)
- [Information Technology Act, 2000](https://www.indiacode.nic.in/bitstream/123456789/13116/1/it_act_2000_updated.pdf)

The seed indexes the corpus. After editing the summaries or enabling the local embedding model, run `python ../scripts/ingest_law.py` from the backend with the project installed.
