const { ethers } = require("ethers");
const fs = require("fs");

async function main() {
    // 连接到本地或指定网络节点
    const provider = new ethers.providers.JsonRpcProvider("http://localhost:8545");
    const signer = provider.getSigner();

    // 读取 VideoNFT.json 获取部署信息
    const videoNFTJSON = JSON.parse(fs.readFileSync("./build/contracts/VideoNFT.json", "utf8"));
    const networks = videoNFTJSON.networks;
    const networkIDs = Object.keys(networks);
    if (networkIDs.length === 0) {
        console.error("Error: VideoNFT.json 中没有找到已部署的网络信息");
        process.exit(1);
    }
    const videoNFTAddress = networks[networkIDs[0]].address;
    const videoNFTAbi = videoNFTJSON.abi;
    if (!videoNFTAddress || !videoNFTAbi) {  
        console.error("Error: 无法从 VideoNFT.json 中提取地址或 ABI 信息");
        process.exit(1);
    }
    console.log("VideoNFT 合约地址:", videoNFTAddress);

    // 实例化 VideoNFT 合约对象
    const videoNFTContract = new ethers.Contract(videoNFTAddress, videoNFTAbi, signer);

    // 查询已铸造的 NFT 数量（tokenCounter）
    const tokenCounter = await videoNFTContract.tokenCounter();
    console.log("已铸造的 NFT 数量:", tokenCounter.toString());

    // 遍历所有 NFT，查询每个 NFT 的 tokenURI 和所有者
    for (let i = 0; i < tokenCounter; i++) {
        try {
            const tokenURI = await videoNFTContract.tokenURI(i);
            const owner = await videoNFTContract.ownerOf(i);
            console.log(`NFT ID: ${i}, tokenURI: ${tokenURI}, owner: ${owner}`);
        } catch (error) {
            console.error(`查询 NFT ID ${i} 时出错:`, error);
        }
    }
}

main();
